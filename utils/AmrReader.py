import os
import re
import pickle


class AMRReader:

    def __init__(self, amr_path: str, output_path: str) -> str:
        self.amr_path = amr_path
        self.output_path = os.path.join(output_path, 'data')
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def build_corpus(self) -> dict:
        align_amr_path = os.path.join(self.amr_path, 'data/alignments/split')
        amrs_path = os.path.join(self.amr_path, 'data/amrs/split')
        file_type = {}
        self.amr_corpus = {}
        for root, dirs, files in os.walk(amrs_path):
            for body_file in files:
                if 'proxy' in body_file:
                    infile = open(os.path.join(root, body_file))
                    m = re.match(r'.*-(.*)-proxy.txt', body_file)
                    file_type[m.group(1)] = self.__extract_attr_file(infile)
        for root, dirs, files in os.walk(align_amr_path):
            for body_file in files:
                if 'proxy' in body_file:
                    infile = open(os.path.join(root, body_file))
                    m = re.match(r'.*-(.*)-proxy.txt', body_file)
                    self.amr_corpus[m.group(1)] = self.__load_AMR(file_type[m.group(1)], infile)
        return self.amr_corpus


    def __extract_attr_file(self, infile):
        """
        This function takes the non-alignment AMR and extract the sentence type. Only the non-alignment AMR file
        contain the sentence type
        """
        first_line = True
        snt_type = ''
        snt_id = ''
        amr_attr = {}
        for line in infile:
            line = line.rstrip()
            if line == '':
                # Only process line that contain snt_id and snt_type
                if not first_line:
                    if snt_id != '':
                        if snt_type:
                            amr_attr[snt_id] = snt_type
                        else:
                            amr_attr[snt_id] = 'body'
                first_line = False

            # Read sentence tokens
            if line.startswith('#'):
                fields = line.split('::')
                for field in fields[1:]:
                    tokens = field.split()
                    if tokens[0] == 'id':
                        snt_id = tokens[1]
                    if tokens[0] == 'snt-type':
                        snt_type = tokens[1]
                continue
        return amr_attr

    def __load_AMR(self, amr_attr, infile):
        '''
        Read from the file and store it in corpus. The corpus comprises of the processed nodes and tokens indexed by ID
        '''
        corpus = {}
        amr_string = ''
        snt_tok = ''
        amr_counter = 0
        for line in infile:
            line = line.rstrip()
            # Every AMR graph is ended by an empty line
            if line == '':
                # This happen on the first line of the file
                if amr_string == '':
                    continue
                else:
                    if snt_id in amr_attr:
                        doc_id = '.'.join(snt_id.split('.')[:-1])
                        body_corpus = corpus.setdefault(doc_id, {})
                        m = re.match(r'.*\.(.*)', snt_id)
                        amr = {}
                        amr['type'] = amr_attr[snt_id]
                        amr['tok'] = snt_tok
                        amr['amr'] = amr_string
                        body_corpus[m.group(1)] = amr
                        corpus[doc_id] = body_corpus
                        amr_counter += 1
                    amr_string = ''
                    continue

            # Read sentence tokens
            if line.startswith('#'):
                fields = line.split('::')
                for field in fields[1:]:
                    tokens = field.split()
                    if tokens[0] == 'id':
                        snt_id = tokens[1]
                    if tokens[0] == 'tok':
                        snt_tok = tokens[1:]
                continue

            # If line is not start by # and not empty means it's part of AMR graph
            amr_string += line + '\n'

        return corpus

    def save_data(self):
        output_file = open(os.path.join(self.output_path, 'amr_corpus.pickle'), 'wb')
        pickle.dump(self.amr_corpus, output_file, -1)

    def load_data(self):
        infile = open(os.path.join(self.output_path, 'amr_corpus.pickle'), 'rb')
        self.amr_corpus = pickle.load(infile)
        return self.amr_corpus

if __name__ == '__main__':
    amr_reader = AMRReader('/home/acp16hh/Data/abstract_meaning_representation_amr_2.0/', '/home/acp16hh/Projects/Research/Exp_7_Improve_CMap/dataset/output')
    amr_reader.build_corpus()
    amr_reader.save_data()