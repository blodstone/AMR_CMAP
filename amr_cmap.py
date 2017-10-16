"""Convert document AMRs to one cmap representations.

@Author: Hardy
"""


import argparse
from sklearn.neural_network import MLPRegressor
from utils.AmrReader import AMRReader
from utils.PropBankReader import PropBankReader
from amr_lib.AMRtoCMap import AMRCorpusExtConverter


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--amr_path', help='Gold standard AMR directory.')
    parser.add_argument('--output_path', help='Output directory.')
    parser.add_argument('--propbank_path', help='Propbank directory.')
    args = parser.parse_args()
    if not args.amr_path:
        raise Exception("No AMR directory is specified.")
    if not args.output_path:
        raise Exception("No output directory is specified.")
    if not args.propbank_path:
        raise Exception("No propbank directory is specified.")
    return args


def main(args):
    amr_reader = AMRReader(args.amr_path, args.output_path)
    propbank_reader = PropBankReader(args.propbank_path, args.output_path)
    amr_corpus = amr_reader.load_data()
    propbank_data = propbank_reader.load_data()
    amr_corpus_ext_converter = AMRCorpusExtConverter(amr_corpus, propbank_data, args.output_path)
    amr_corpus_ext = amr_corpus_ext_converter.load_data()


    print()




if __name__ == '__main__':
    args = init_args()
    main(args)