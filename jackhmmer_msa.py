import os
import argparse
import json
import pickle
from msa_generation import get_msa_jackhmmer
from msa_generation.msa_utils import create_ram_disk, read_fasta, create_directory, save_dict_to_fasta
import time


def reformat_sequences(input_msa):
    """
    Reformat sequences from MSA for use in colabfold_batch.

    Args:
        input_msa (list): List of sequences from the MSA.

    Returns:
        list: Formatted sequences in FASTA format.
    """
    formatted_sequences = []
    for idx, sequence in enumerate(input_msa[0]):
        formatted_sequence = f">sequence_{idx + 1}\n{sequence}\n"
        formatted_sequences.append(formatted_sequence)
    return formatted_sequences


def convert_msa(filename):
    """
    Convert the MSA pickle file to a formatted sequence list.

    Args:
        filename (str): Path to the MSA pickle file.

    Returns:
        list: Converted and formatted sequences from the MSA.
    """
    with open(filename, 'rb') as f:
        msa_data = pickle.load(f)

    msa_list = msa_data['msas']
    converted_msa = reformat_sequences(msa_list)
    return converted_msa


def save_formatted_sequences_to_file(formatted_sequences, output_file):
    """
    Save the formatted sequences to a file.

    Args:
        formatted_sequences (list): List of formatted sequences.
        output_file (str): Path to save the formatted sequences.
    """
    with open(f'{output_file}', 'w') as f:
        for sequence in formatted_sequences:
            f.write(sequence)


def prepare_os():
    """
    Prepare the operating system environment by creating a RAM disk.
    """
    create_ram_disk()


def build_msa(sequence, jobname, complete_output_dir, homooligomer, tmp_dir, use_ramdisk):
    """
    Build the MSA using jackhmmer for the target sequence.

    Args:
        sequence (str): The target sequence for MSA.
        jobname (str): The job name.
        complete_output_dir (str): The output directory path.
        homooligomer (int): The number of copies of the protein.
        tmp_dir (str): Temporary directory path.
        use_ramdisk (bool): Whether to use a RAM disk for the process.
    """
    prepped_msa = get_msa_jackhmmer.prep_inputs(sequence, jobname, homooligomer,  output_dir=complete_output_dir)

    get_msa_jackhmmer.prep_msa(prepped_msa, msa_method='jackhmmer', add_custom_msa=False, msa_format="fas",
                               pair_mode="unpaired", pair_cov=50, pair_qid=20, TMP_DIR=tmp_dir, use_ramdisk=use_ramdisk)


def main():
    """
    Main function that handles command-line arguments and initiates the MSA building process.
    """
    parser = argparse.ArgumentParser(description="Assemble MSA for target sequence with jackhmmer")
    parser.add_argument('--jobname', type=str, help="The job name", default='jackhmmer_job')
    parser.add_argument('--sequence_path', type=str, help="Path to a .fasta file containing the target sequence for MSA building")
    parser.add_argument('--output_path', type=str, help="Path to save results to", default='.')
    parser.add_argument('--homooligomers', type=int, help="Number of copies of the protein", default=1)
    parser.add_argument('--use_ramdisk', type=bool, help="Mounts a ramdisk for dramatically speeding up jackhmmer search (requires root access)", default=True)

    args = parser.parse_args()

    config = {}

    # Override config with command line arguments if provided
    config['jobname'] = args.jobname 
    config['sequence_path'] = args.sequence_path 
    config['output_path'] = args.output_path 
    config['homooligomers'] = args.homooligomers
    config['use_ramdisk'] = args.use_ramdisk 
    config['tmp_dir'] = "tmp"

    if config['sequence_path'] is None:
        raise ValueError("Sequences file must be provided via --sequences_file or in the config file.")
    if not os.path.exists(config['sequence_path']):
        raise FileNotFoundError(f"Sequences file {config['sequence_path']} not found.")
    if not os.path.isdir(config['output_path']):
        raise NotADirectoryError(f"Output path {config['output_path']} is not a directory.")
    if not isinstance(config['homooligomers'], int) or config['homooligomers'] <= 0:
        raise ValueError("Homooligomers must be a positive integer.")

    build_jackhmmer_msa(config)


def build_jackhmmer_msa(config):
    """
    Build the MSA using jackhmmer for the target sequence based on the provided configuration.

    Args:
        config (dict): Configuration dictionary containing all necessary parameters.
    """
    print("starting")
    create_directory(f'{config["output_path"]}/{config["jobname"]}/msas/jackhmmer')
    create_directory(f'{config["output_path"]}/{config["jobname"]}/target_seq/')
    print("directories created")
    sequence_dict = read_fasta(config['sequence_path'])
    save_dict_to_fasta(sequence_dict, config['output_path'], config['jobname'])

    sequence_name = list(sequence_dict.keys())[0]
    config['sequence_string'] = list(sequence_dict.values())[0]

    print(f"\nRunning jackhmmer MSA building for target sequence at {config['sequence_path']}\n")

    print(f"{sequence_name}: \n{config['sequence_string']}\n")

    print("Configurations:")
    print("***************************************************************")
    print(f"Job Name: {config['jobname']}")
    print(f"Sequence File Path: {config['sequence_path']}")
    print(f"Output Path: {config['output_path']}")
    print(f"Homooligomers: {config['homooligomers']}")
    print(f"Use ramdisk? {config['use_ramdisk']}")
    print("***************************************************************\n")

    # optionally create ramdisk
    if config["use_ramdisk"]:
        prepare_os()
    # sets output directory for MSA
    complete_output_dir = f"{config['output_path']}/{config['jobname']}/msas/jackhmmer/"
    time.sleep(3)
    # builds jackhmmer MSA from target sequence
    build_msa(config["sequence_string"], config["jobname"], complete_output_dir, config["homooligomers"], tmp_dir=config["tmp_dir"], use_ramdisk=config["use_ramdisk"])

    # reformats MSA to something colabfold_batch can use
    converted_msa = convert_msa(f"{complete_output_dir}/msa.pickle")
    save_formatted_sequences_to_file(converted_msa, f"{complete_output_dir}/{config['jobname']}.a3m")

    print(f'\nSaved {config["jobname"]} jackhmmer MSA to {complete_output_dir}/{config["jobname"]}.a3m\n')


if __name__ == "__main__":
    main()
