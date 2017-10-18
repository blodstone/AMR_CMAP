import re
import pickle
import os
from collections import defaultdict
from amr_hackathon import amr
from utils.PropBankReader import PropBankReader
from utils.AmrReader import AMRReader


class AMRtoTriples:

    def __init__(self, amr_data, propbank):
        self.amr_data = amr_data
        self.propbank = propbank
        self.triples_linkers = None
        self.triples = {}
        self.amr_obj = amr.AMR(self.amr_data['amr'], self.amr_data['tok'])
        self.var2c = self.amr_obj.var2concept()


    def convert(self) -> dict:
        """
        Convert an AMR data to list of triples
        """
        def get_triples_linker():
            """
            Retrieve all of the triples linking phrases from the AMR object.
            We use the Framenet words that are found in the AMR Object as the linker.
            """
            triples_linkers = []
            concepts = list(self.amr_obj.concepts())

            # Retrieve all concept that has the word ARG in it
            for concept in concepts:
                triple = self.amr_obj.triples(head=concept[0])
                items = [item for item in triple if 'ARG' in item[1]]
                if len(items) > 0:
                    triples_linkers.append(triple)
            return triples_linkers

        def generate_triples():

            def fixing_annotation(key, n):
                """
                Fixing some inconsistency in the annotation
                """
                if key + '.' + n not in self.propbank:
                    key = key.replace('-', '_')
                return key + '.' + n

            def is_agent(f_rel, rel_var):
                """
                Checking whether the role is an agent (denoted by 'pag') or not
                """
                # TODO: beside 'pag' is there any other role?
                m = re.match(r'(.*)-(\d*)$', rel_var)
                key = m.group(1)
                n = m.group(2)

                # some annotation does not have the correspondence frameset, just put false if found
                if n == '00':
                    return False

                concept = fixing_annotation(key, n)
                roleset = self.propbank[concept]

                m = re.match(r':ARG(.).*', f_rel[1])
                n = int(m.group(1))
                roles = roleset.getElementsByTagName('role')

                for role in roles:
                    if dict(role.attributes)['n'].value == str(n) and dict(role.attributes)['f'].value.lower() == 'pag':
                        return True
                return False

            # Case 1: ARG
            for triple_linker in self.triples_linkers:
                triple = [None, triple_linker[0][0], []]
                for rel in triple_linker:
                    if 'ARG' in rel[1] and 'of' not in rel[1]:
                        # check whether the propbank verb rel[0] and its argument rel[2] is an agent or not
                        if is_agent(rel, self.var2c[rel[0]].__str__()):
                            triple[0] = rel[2]
                        else:
                            triple[2].append(rel[2])
                if not (triple[0] is None and triple[2] == []):
                    self.triples[triple[1]] = triple

            # Case 2: ARG-of
            for triple_linker in self.triples_linkers:
                for rel in triple_linker:
                    if 'ARG' in rel[1] and 'of' in rel[1]:
                        if rel[2] not in self.triples:
                            self.triples[rel[2]] = [None, rel[2], []]
                        if is_agent(rel, self.var2c[rel[2]].__str__()):
                            self.triples[rel[2]][0] = rel[0]
                        else:
                            self.triples[rel[2]][2].append(rel[0])
            return self.triples

        self.triples_linkers = get_triples_linker()
        return generate_triples()

    def generate_amr_string_from_triples(self):
        """
        Given a triple, generate an amr string from it
        """
        def get_alignment(f_concept_var):
            """
            Get alignment for a single concept
            """
            for triplet, a in self.amr_obj.alignments().items():
                if f_concept_var == triplet[0] and triplet[1] == ':instance-of':
                    return int(a.split('.')[1].split(',')[0])

        def get_all_amr_string(f_concept_var):
            """
            Get all amr string from the concept
            """
            def get_triples(key):
                result_triples = []
                f_triples = self.amr_obj.triples(dep=key, rel=':ARG-of', normalize_inverses=True)
                if f_triples:
                    result_triples.extend(f_triples)
                f_triples = self.amr_obj.triples(head=key)
                if f_triples:
                    result_triples.extend(f_triples)
                return result_triples
            entry = defaultdict(int)
            q = []
            q.append((amr.Var('TOP'), ':top', f_concept_var))
            entry[f_concept_var] += 1
            reentrancies = self.amr_obj.reentrancies()
            all_triples = []
            while q:
                u = q.pop()
                all_triples.append(u)
                triples = get_triples(u[2])
                for triplet in triples[::-1]:
                    if triplet[2] in reentrancies:
                        if entry[triplet[2]] <= reentrancies[triplet[2]] + 1:
                            q.append(triplet)
                            entry[triplet[2]] += 1
                    else:
                        q.append(triplet)
                        entry[triplet[2]] += 1
            s = ''
            stack = []
            instance_fulfilled = None
            align = role_align = {}
            concept_stack_depth = {
                None: 0}  # size of the stack when the :instance-of triple was encountered for the variable
            for h, r, d in all_triples + [(None, None, None)]:
                align_key = align.get((h, r, d), '')
                role_align_key = role_align.get((h, r, d), '')
                if r == ':top':
                    s += '(' + d()
                    stack.append((h, r, d))
                    instance_fulfilled = False
                elif r == ':instance-of':
                    s += ' / ' + d(align_key)
                    instance_fulfilled = True
                    concept_stack_depth[h] = len(stack)
                elif r == ':wiki':
                    continue
                elif h == stack[-1][2] and r == ':polarity':  # polarity gets to be on the same line as the concept
                    s += ' ' + r + role_align_key + ' ' + d(align_key)
                else:
                    while len(stack) > concept_stack_depth[h]:
                        h2, r2, d2 = stack.pop()
                        if instance_fulfilled is False:
                            # just a variable or constant with no concept hanging off of it
                            # so we have an extra paren to get rid of
                            align_key2 = align.get((h2, r2, d2), '')
                            s = s[:-len(d2(align_key2)) - 1] + d2(align_key2, append=not instance_fulfilled)
                        else:
                            s += ')'
                        instance_fulfilled = None
                    if d is not None:
                        s += ' \n' + ' ' * 4 * len(stack) + r + role_align_key + ' (' + d(align_key)
                        stack.append((h, r, d))
                        instance_fulfilled = False
            return s

        # def get_all_alignments(concept_var, sep, left=True):
        #     '''
        #     Get all alignments from the concept
        #     '''
        #
        #     # def alignment_to_text(alignments):
        #     #     '''
        #     #     Convert all alignments to text
        #     #     '''
        #     #     def filter(idxs, tol):
        #     #         '''
        #     #         Resulting only the longest contiguous elements
        #     #         '''
        #     #         diffs = [idxs[i + 1] - idxs[i] for i in range(len(idxs) - 1)]
        #     #         start = False
        #     #         max_length = -1
        #     #         for i in range(len(diffs)):
        #     #             if diffs[i] <= tol:
        #     #                 if not start:
        #     #                     start = True
        #     #                     length = 1
        #     #                     start_idx = i
        #     #                 else:
        #     #                     length += 1
        #     #             else:
        #     #                 if start:
        #     #                     start = False
        #     #                     end_idx = i
        #     #                     if length >= max_length:
        #     #                         max_length = length
        #     #                         max_start_idx = start_idx
        #     #                         max_end_idx = end_idx
        #     #         if start:
        #     #             end_idx = i + 1
        #     #             if length >= max_length:
        #     #                 max_start_idx = start_idx
        #     #                 max_end_idx = end_idx
        #     #         return [idxs[i] for i in range(max_start_idx, max_end_idx + 1)]
        #     #
        #     #     doc = en_nlp(" ".join(self.amr_obj.tokens()))
        #     #     alignments = sorted(list(set(alignments)))
        #     #     # We used noun chunks to prevent orphaned noun
        #     #     noun_chunks = list(doc.noun_chunks)
        #     #     new_alignments = set()
        #     #     for a in alignments:
        #     #         new_alignments.add(a)
        #     #         # Insert all noun chunks to new alignment
        #     #         for noun in noun_chunks:
        #     #             if noun.start <= a <= noun.end:
        #     #                 new_alignments.update([i for i in range(noun.start, noun.end)])
        #     #     text = [self.amr_obj.tokens()[idx] for idx in filter(sorted(list(new_alignments)), 3)]
        #     #     text = " ".join(text)
        #     #     return text
        #
        #     def get_triplet(key):
        #         result_triplets = []
        #         triples = self.amr_obj.f_triples(dep=key, rel=':ARG-of', normalize_inverses=True)
        #         if triples:
        #             result_triplets.extend(triples)
        #         triples = self.amr_obj.f_triples(head=key)
        #         if triples:
        #             result_triplets.extend(triples)
        #         return result_triplets
        #
        #     triplets_stor = {}
        #     entry = defaultdict(int)
        #     q = queue.Queue()
        #     q.put(concept_var)
        #     entry[concept_var] += 1
        #     result_alignments = []
        #     alignments = self.amr_obj.alignments()
        #     role_alignments = self.amr_obj.role_alignments()
        #     reentrancies = self.amr_obj.reentrancies()
        #     while not q.empty():
        #         u = q.get()
        #         triples = get_triplet(u)
        #         for triplet in triples:
        #             if triplet not in triplets_stor:
        #                 triplets_stor[triplet] = 0
        #             if type(triplet[2]) is amr.Var:
        #                 if entry[triplet[2]] <= reentrancies[triplet[2]] + 1:
        #                     q.put(triplet[2])
        #                     entry[triplet[2]] += 1
        #
        #             def is_pos_correct(idx, sep, left=True):
        #                 if left:
        #                     return True if idx < sep else False
        #                 else:
        #                     return True if idx > sep else False
        #
        #             if triplet in alignments:
        #                 idx = int(alignments[triplet].split('.')[1])
        #                 #if is_pos_correct(idx, sep, left):
        #                 result_alignments.append(idx)
        #             if triplet in role_alignments:
        #                 idx = int(role_alignments[triplet].split('.')[1])
        #                 #if is_pos_correct(idx, sep, left):
        #                 result_alignments.append(idx)
        #     return alignment_to_text(result_alignments)

        if self.triples == {}:
            return ''

        results = []
        for key, triple in self.triples.items():
            result_1 = get_alignment(triple[1])
            if result_1 is None:
                continue
            if triple[0] is not None:
                result_0 = get_all_amr_string(triple[0])
            else:
                result_0 = ''
            for concept_var in triple[2]:
                if concept_var:
                    result_2 = get_all_amr_string(concept_var)
                    if len(result_2.split(' ')) == 1:
                        if not result_2.startswith('('):
                            result_2 = '(' + result_2 + ')'
                    results.append((result_0, self.amr_obj.var2concept()[triple[1]]._name, result_2))

        # f = open('amr_string.txt', 'w')
        # for l, m, r in results:
        #     if l != '':
        #         f.write(l+'\n')
        #     if r != '':
        #         f.write(r+'\n')
        # f.close()
        return results


class AMRCorpusExtConverter:
    """
    Read the amr corpus and update the amr with triples
    """
    def __init__(self, c_amr_corpus, c_propbank_data, output_path):
        self.amr_corpus = c_amr_corpus
        self.propbank_data = c_propbank_data
        self.output_path = os.path.join(output_path, 'data')

    def update_amr_corpus_with_triples(self):
        for dataset_name, dataset in self.amr_corpus.items():
            for doc_name, doc in dataset.items():
                for amr_id, amr_data in doc.items():
                    amr_to_triples = AMRtoTriples(amr_data, self.propbank_data)
                    self.amr_corpus[dataset_name][doc_name][amr_id]['triples'] = amr_to_triples.convert()
                    self.amr_corpus[dataset_name][doc_name][amr_id]['amr_string_triples'] \
                        = amr_to_triples.generate_amr_string_from_triples()
        return self.amr_corpus

    def write_tok_to_file(self):
        """
        Write tok to file, for openIE relation extraction later
        """
        dir_path = os.path.join(self.output_path, 'tokens')
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        for dataset_name, dataset in self.amr_corpus.items():
            f = open(os.path.join(dir_path, dataset_name + '_tok.txt'), 'w')
            for doc_name, doc in dataset.items():
                for amr_id, amr_data in doc.items():
                    amr_strings = self.amr_corpus[dataset_name][doc_name][amr_id]['amr_string_triples']
                    if not amr_strings:
                        continue
                    tok = ' '.join(self.amr_corpus[dataset_name][doc_name][amr_id]['tok'])
                    f.write(tok + '\n')
            f.close()

    def write_amr_string_to_file(self):
        """
        Write amr_string from each triple to file, for use by AMR generation
        """
        dir_path = os.path.join(self.output_path, 'amr_string')
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
        for dataset_name, dataset in self.amr_corpus.items():
            f = open(os.path.join(dir_path, dataset_name + '_amr_string.txt'), 'w')
            for doc_name, doc in dataset.items():
                for amr_id, amr_data in doc.items():
                    amr_strings = self.amr_corpus[dataset_name][doc_name][amr_id]['amr_string_triples']
                    for left, middle, right in amr_strings:
                        if left != '':
                            f.write(left+'\n')
                        if right != '':
                            f.write(right+'\n')
            f.close()

    def write_triples_to_files(self):
        for dataset_name, dataset in self.amr_corpus.items():
            if dataset_name != 'dev':
                continue
            f = open('/home/acp16hh/Projects/Research/Exp_7_Improve_CMap/lib/amr2eng/sample/sample.out', 'r')
            f_openie = open('/home/acp16hh/Projects/Research/Exp_7_Improve_CMap/lib/openie-standalone/openie_dev.out', 'r')
            f_out = open(dataset_name + '_out.txt', 'w')
            openie_content = f_openie.readlines()
            content = f.readlines()
            idx = 0
            idx_openie = 0
            for doc_name, doc in dataset.items():
                for id, amr_data in doc.items():
                    amr_strings = self.amr_corpus[dataset_name][doc_name][id]['cmaps_text']
                    if not amr_strings:
                        continue
                    tok = ' '.join(self.amr_corpus[dataset_name][doc_name][id]['tok'])
                    f_out.write('Document Name : ' + doc_name + '.' + id + '\n')
                    f_out.write('Sentence: ' + tok + '\n')
                    f_out.write('AMR: ' + self.amr_corpus[dataset_name][doc_name][id]['amr'] + '\n')
                    f_out.write('Triplets: \n')
                    count = 1
                    for l, m, r in amr_strings:
                        f_out.write('[' + str(count) + ']: \n')
                        count += 1
                        nlg = ['', '', '']
                        if l != '':
                            nlg[0] = content[idx].rstrip()
                            idx += 1
                        nlg[1] = m
                        if r != '':
                            nlg[2] = content[idx].rstrip()
                            idx += 1
                        f_out.write(str(nlg) + '\n')
                        if l != '':
                            f_out.write('Left: \n' + l + '\n')
                        f_out.write('Middle: ' + m + '\n')
                        if r != '':
                            f_out.write('Right: \n' + r + '\n\n')
                    f_out.write('OpenIE Triplets: \n')
                    first = True
                    while openie_content[idx_openie] != '\n':
                        if first:
                            first = False
                            idx_openie += 1
                            continue
                        f_out.write(openie_content[idx_openie])
                        idx_openie += 1
                    idx_openie += 1
                    f_out.write('\n\n')
            f.close()
            f_out.close()

    def is_file_exist(self):
        """
        Checking whether the file exist or not
        """
        return os.path.isfile(os.path.join(self.output_path, 'amr_corpus_ext.pickle'))

    def save_data(self):
        output_file = open(os.path.join(self.output_path, 'amr_corpus_ext.pickle'), 'wb')
        pickle.dump(self.amr_corpus, output_file, -1)

    def load_data(self):
        infile = open(os.path.join(self.output_path, 'amr_corpus_ext.pickle'), 'rb')
        self.amr_corpus = pickle.load(infile)
        return self.amr_corpus


if __name__ == '__main__':
    amr_reader = AMRReader('/home/acp16hh/Data/abstract_meaning_representation_amr_2.0/',
                           '/home/acp16hh/Projects/Research/Exp_7_Improve_CMap/dataset/output')
    propbank_reader = PropBankReader(
        '/home/acp16hh/Projects/Research/Exp_7_Improve_CMap/dataset/Input/propbank-frames/frames',
        '/home/acp16hh/Projects/Research/Exp_7_Improve_CMap/dataset/output')
    amr_corpus = amr_reader.load_data()
    propbank_data = propbank_reader.load_data()

    amr_corpus_ext = AMRCorpusExtConverter(amr_corpus, propbank_data, '/home/acp16hh/Projects/Research/Exp_7_Improve_CMap/dataset/output')
    amr_corpus_ext.load_data()
    # amr_corpus_ext.generate_tok()
    # amr_corpus_ext.convert_amr_to_cmaps()
    # amr_corpus_ext.save_amr_string_to_txt()
    # amr_corpus_ext.save_data()
    amr_corpus_ext.write_triples_to_files()







