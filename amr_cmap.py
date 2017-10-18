"""
Convert document AMRs to one cmap representations.

@Author: Hardy
"""
import argparse
from sklearn.neural_network import MLPRegressor
from utils.AmrReader import AMRReader
from utils.PropBankReader import PropBankReader
from amr_lib.AMRtoTriples import AMRCorpusExtConverter


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--amr_path', help='Gold standard AMR directory.')
    parser.add_argument('--output_path', help='Output directory.')
    parser.add_argument('--propbank_path', help='Propbank directory.')
    parser.add_argument('--gen_token', help='Generate token for OpenIE.', action='store_true')
    parser.add_argument('--gen_amr_string_triples', help='Generate AMR string triples for AMR generator',
                        action='store_true')
    parser.add_argument('--write_triples', help='Write triples to files', action='store_true')
    args = parser.parse_args()
    if not args.amr_path:
        raise Exception("No AMR directory is specified.")
    if not args.output_path:
        raise Exception("No output directory is specified.")
    if not args.propbank_path:
        raise Exception("No propbank directory is specified.")
    return args


def main(args):
    # initialize AMR Reader for loading the amr corpus
    amr_reader = AMRReader(args.amr_path, args.output_path)
    # if amr_corpus file doesn't exist rebuild the corpus and save data
    if amr_reader.is_file_exist():
        amr_corpus = amr_reader.load_data()
    else:
        amr_corpus = amr_reader.build_corpus()
        amr_reader.save_data()

    # initialize Propbank Reader for loading the probank data
    propbank_reader = PropBankReader(args.propbank_path, args.output_path)
    if propbank_reader.is_file_exist():
        propbank_data = propbank_reader.load_data()
    else:
        propbank_data = propbank_reader.build_data()
        propbank_reader.save_data()


    amr_corpus_ext_converter = AMRCorpusExtConverter(amr_corpus, propbank_data, args.output_path)

    # update amr_corpus with triples
    if amr_corpus_ext_converter.is_file_exist():
        amr_corpus = amr_corpus_ext_converter.load_data()
    else:
        amr_corpus = amr_corpus_ext_converter.update_amr_corpus_with_triples()
        amr_corpus_ext_converter.save_data()

    # exit program when finished
    if args.gen_token or args.gen_amr_string_triples:
        if args.gen_token:
            amr_corpus_ext_converter.write_tok_to_file()
        if args.gen_amr_string_triples:
            amr_corpus_ext_converter.write_amr_string_to_file()
        return

    if args.write_triples:
        amr_corpus_ext_converter.write_triples_to_files()



    print()




if __name__ == '__main__':
    args = init_args()
    main(args)