import pandas as pd
import numpy as np
from pyplink import PyPlink

plink_file_prefix = "/home/dream/PEGS_genomic_data/SNVs_small_indels/val/PEGS_GWAS_genotypes_v1.1_val_synthetic"
output_dir = "/home/dream/PEGS_genomic_data/SNVs_small_indels/val/"


# Load the list of SNPs from the additional CSV file
prs_snp_list_file = '/home/dream/PEGS_genomic_data/SNVs_small_indels/processing_codes/hypercholesterolemia_snps.txt'  # Replace with the actual path to your file
prs_snp_list_df = pd.read_csv(prs_snp_list_file, header=None, names=['snp'])
valid_snp_ids_phenotype = set(prs_snp_list_df['snp'].str.strip())

 
        
try:
    # Load BIM and FAM files
    with PyPlink(plink_file_prefix) as plink:
        bim = plink.get_bim()
        fam = plink.get_fam()

    # Create DataFrames but only keep relevant columns
    bim_df = pd.DataFrame(bim, columns=["chrom", "snp", "pos", "a1", "a2"])  # Excluded 'cm'
    fam_df = pd.DataFrame(fam, columns=["fid"]) 
    fam_df = fam_df.rename(columns={"fid": "EPR_identifier"})

    print("BIM and FAM files loaded successfully.")

    # Handle Missing rsIDs and '*' Alleles
    bim_df['a1'] = bim_df['a1'].replace('*', 'unknown')
    bim_df['a2'] = bim_df['a2'].replace('*', 'unknown')

    # Assuming the custom format is [Chromosome Number]:[Coordinate], as stated in README
    bim_df['snp'] = bim_df.apply(lambda row: f"chr{row['chrom']}:{row['pos']}" if pd.isna(row['snp']) else row['snp'], axis=1)

    print("BIM DataFrame processed successfully.")

    # Extract Genotypes
    genotypes = []
    with PyPlink(plink_file_prefix) as plink:
        for gt in plink:
            genotypes.append(gt[1])  # Store genotype array

    genotypes_arr = np.array(genotypes, dtype='int8').T  # Transpose to have individuals as rows and SNPs as columns
    print("Genotype array created successfully.")

    # Identify SNPs to keep (i.e., without any -1 values across all samples)
    snps_without_missing_values_mask = np.all(genotypes_arr != -1, axis=0)

    # Identify SNPs with known alleles (i.e., not 'unknown')
    known_alleles_mask = (bim_df['a1'] != 'unknown') & (bim_df['a2'] != 'unknown')

    # Combine the masks to identify SNPs to keep
    snps_to_keep_mask = snps_without_missing_values_mask & known_alleles_mask & bim_df.index.isin(valid_snp_ids_phenotype) # It's a boolean!

    # Check the number of SNPs to keep (number of True values)
    num_snps_to_keep = np.sum(snps_to_keep_mask)
    print(f"Number of SNPs to keep: {num_snps_to_keep}")

    # Check the total number of SNPs
    total_snps = len(snps_to_keep_mask)
    print(f"Total number of SNPs: {total_snps}")

    # Optionally, print the proportion of SNPs to keep
    proportion_snps_to_keep = num_snps_to_keep / total_snps
    print(f"Proportion of SNPs to keep: {proportion_snps_to_keep:.2f}")

    # Get the list of SNP IDs to keep
    snps_to_keep = bim_df.index[snps_to_keep_mask].tolist()

    # Filter the genotype array to keep only SNPs without any -1 values and with known alleles
    genotypes_filtered = genotypes_arr[:, snps_to_keep_mask]

    # Create a DataFrame with EPR identifiers as rows and SNPs as columns
    final_df = pd.DataFrame(genotypes_filtered, index=fam_df['EPR_identifier'], columns=snps_to_keep)


    print(f"Final DataFrame shape: {final_df.shape}")

    # Extract base name for the output files
    base_name = plink_file_prefix.split('/')[-1]

    final_df.to_pickle(f'{output_dir}{base_name}.pickle')
    
    print("DataFrame has been saved in chunks as pickle files.")

except Exception as e:
    print(f"An error occurred: {e}")
