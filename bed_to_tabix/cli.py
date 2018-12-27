#!/usr/bin/env python
"""
Welcome to bed_to_tabix! This tool will download the genotypes from
The 1,000 Genomes Proyect's in the regions defined in one or more BED files.

Usage:
    bed_to_tabix --in BEDFILE... [options]
    bed_to_tabix (--help | --version)

Options:
    --in BEDFILE...   One or more input .bed file(s) with the genomic
                      regions to download. Mandatory argument(s). Repeat
                      the --in flag with a different .bed each time for more
                      than one input file.

    --out VCFFILE     Output filepath for the VCF. You don't need to add
                      '.vcf' to the name. If not set, bed_to_tabix will
                      use the input filepath and replace .bed with .vcf.gz.
                      WARNING: if a file with the same filename exists, it
                      will be overwritten without asking.
    --threads N       Perform the downloads in N parallel threads. Default: 6.

    --unzipped        If set, the downloaded VCF will not be gzipped.

    -f --force        If set, it will overwrite the output file if it exists.

    --dry-run         If set, it will just print the tabix commands to
                      STDOUT, instead of running them.

    --debug           Run in DEBUG logging mode. It will print the comands
                      being run at each step.

    --no-cleanup      Don't remove the temporary files after finishing.
                      Useful for debugging.

    --path-to-bcftools PATH    Full path to bcftools executable.
                               If not present, the ENV variable
                               PATH_TO_BCFTOOLS will be searched for.

    --path-to-tabix PATH       Full path to tabix executable.
                               If not present, the ENV variable
                               PATH_TO_TABIX will be searched for.

    --path-to-bgzip PATH       Full path to bgzip executable.
                               If not present, the ENV variable
                               PATH_TO_BGZIP will be searched for.

    --path-to-java PATH        Full path to java executable.
                               If not present, the ENV variable
                               PATH_TO_JAVA will be searched for.

    --path-to-gatk3 PATH       Full path to gatk3 java file.
                               If not present, the ENV variable
                               PATH_TO_GATK3 will be searched for.

    --path-to-reference-fasta PATH       Full path to the reference fasta for
                                         GATK to use.
                                         If not present, the ENV variable
                                         PATH_TO_REFERENCE_FASTA will be
                                         searched for.

    -h --help         Show this help.
    -v --version      Show version.
"""

import sys
from os import getcwd, environ
from os.path import basename, join, isfile
import logging
from subprocess import CalledProcessError

from docopt import docopt
import coloredlogs

from lib import run_pipeline, cleanup_temp_files
from package_info import PACKAGE_INFO


logger = logging.getLogger(PACKAGE_INFO['PROGRAM_NAME'])

defaults = {
    '--threads': 6,
}

def parse_arguments(arguments):
    if arguments['--version']:
        msg = '{PROGRAM_NAME} {VERSION} ({DATE}) by {AUTHOR}\nCheck: {URL}'
        print(msg.format(**PACKAGE_INFO))
        sys.exit()

    if arguments['--threads']:
        arguments['--threads'] = int(arguments['--threads'])
    else:
        arguments['--threads'] = defaults['--threads']

    if not arguments['--out']:
        filename = '__'.join(basename(bed).replace('.bed', '')
                             for bed in arguments['--in'])
        arguments['--out'] = join(getcwd(), filename)

    if not arguments['--out'].endswith('.vcf'):
        arguments['--out'] += '.vcf'

    if not arguments['--unzipped']:
        arguments['--out'] += '.gz'

    varnames = ['bcftools', 'tabix', 'bgzip', 'gatk3', 'java',
                'reference_fasta']
    for varname in varnames:
        varname = f'path_to_{varname}'
        parameter = '--' + varname.replace('_', '-')
        env_varname = varname.upper()
        if not arguments[parameter]:
            if env_varname in environ:
                arguments[parameter] = environ[env_varname]
            else:
                print(f'Missing either {parameter} ' +
                      f'or ENV variable {env_varname}')
                sys.exit()

    if '--force' not in arguments and isfile(arguments['--out']):
        msg = ('Output file {} already exists!\nUse --force or -f to overwrite '
               'it or change the output filename with --out.')
        logger.warning(msg.format(arguments['--out']))
        sys.exit()

    return arguments


def main():
    arguments = parse_arguments(docopt(__doc__))

    coloredlogs.DEFAULT_LOG_FORMAT = '[@%(hostname)s %(asctime)s] %(message)s'
    loglevel = 'DEBUG' if arguments['--debug'] else 'INFO'
    coloredlogs.install(level=loglevel)

    try:
        run_pipeline(
            bedfiles=arguments['--in'],
            threads=arguments['--threads'],
            outfile=arguments['--out'],
            gzip_output=(not arguments['--unzipped']),
            dry_run=arguments['--dry-run'],
            path_to_bcftools=arguments['--path-to-bcftools'],
            path_to_java=arguments['--path-to-java'],
            path_to_tabix=arguments['--path-to-tabix'],
            path_to_gatk3=arguments['--path-to-gatk3'],
            path_to_bgzip=arguments['--path-to-bgzip'],
            path_to_reference_fasta=arguments['--path-to-reference-fasta'],
            # The FTP option is failing and is not fixed yet:
            # http=arguments['--http'],
        )
    except KeyboardInterrupt:
        logger.warning('User stopped the program. Cleanup and exit.')
        sys.exit()
    except CalledProcessError as error:
        msg = 'The following command failed (code: {0}). Cleanup and exit: {1}'
        logger.warning(msg.format(*error.args))
        sys.exit()
    finally:
        if arguments['--no-cleanup']:
            logger.info('No cleanup requested, leaving the temp files.')
        else:
            logger.info('Cleaning up temporary files.')
            cleanup_temp_files()


if __name__ == '__main__':
    main()