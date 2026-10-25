#!/bin/bash
#SBATCH --array=0-99%2
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --mem=0
echo tampered probe
