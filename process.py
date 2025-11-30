#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
===== input =====
1. the seq number of files, it will be the first word of the txt file names. Sometimes there will be a extra letter appended. (EX: T1571, T1588a)($SUTRA_ID)

2. The Chinese name of the Sutra. It locates on the LAST word of the SECOND line of each file.(EX: 大乘廣百論釋論)($SUTRA_NAME)
3. total txt files in the folder (EX: 10)($SUTRA_VOLS)

You will need to trim off the comment area. (first few line starts with #), EXCEPT the first file (EX: T1571_001.txt)

===== output =====
1. put all txt files into a single one, in sequence.
2. filename will be: $SUTRA_VOLS_《$SUTRA_NAME》.txt


==== folder structure ====
1. Make a project directory, put all XXXX.txt.zip files into that directory.
   Note that each zip file should not contain directory in itself.
2. python this_file.py [project directory]

The script will then extract all XXX.txt.zip files in project directory, into a newly created XXX directory,
and then process all sub-directory in the project directory.

"""

from os import listdir, getcwd, mkdir, remove, makedirs
from os.path import isdir, isfile, join, basename, abspath, dirname
from shutil import rmtree
from glob import glob
import re
import sys
import zipfile
import argparse

def default_logger(msg):
    print(msg)

def process_folder(working_dir, name, output_dir, removeFolder=False, logger=default_logger):
    dirname = join(working_dir, name)
    logger("processing folder %s" % dirname)
    
    # get list of txt files
    txt_list = [f for f in sorted(glob(join(dirname, '*.txt'))) if isfile(f)]
    if not txt_list:
        return

    # Ensure the TOC file (usually first alphabetically or specifically named) is last if needed, 
    # but the original logic was: txt_list = txt_list[1:] + [txt_list[0]]
    # This implies the first file in `sorted` order is the TOC or needs to be moved.
    # Let's keep original logic for safety, assuming standard naming.
    if len(txt_list) > 1:
        txt_list = txt_list[1:] + [txt_list[0]] 

    # get necessary parameters
    sutra_vols = len(txt_list)
    if sutra_vols == 0:
        return
    sutra_id = basename(txt_list[0]).split('_')[0]
    sutra_name = ""
    with open(txt_list[0]) as firstfile:
        try:
            head = [next(firstfile) for x in range(2)]
            if len(head) >= 2:
                tokens = re.split(r'\s+', head[-1])
                if len(tokens) > 0 and len(tokens[-1]) > 0:
                    sutra_name = tokens[-1]
                elif len(tokens) > 1:
                    sutra_name = tokens[-2]
        except StopIteration:
            pass
        pass
    
    logger("SUTRA_NAME: %s\nSUTRA_ID: %s\nSUTRA_VOLS: %d" % \
            (sutra_name, sutra_id, sutra_vols))
    
    # processing all txt files
    is_first = True
    output_filename = join(output_dir, "%s_《%s》.txt" % (sutra_id, sutra_name))
    
    with open(output_filename, 'w') as out:
        for f in txt_list:
            with open(f) as txt:
                for line in txt:
                    if line.startswith('#'):
                        if is_first:
                            out.write(line)
                    else:
                        out.write(line)
                pass
            is_first = False
            pass
        pass
    logger("Finished processing %s" % output_filename)
    # delete dir
    if removeFolder:
        rmtree(dirname)
    pass

def process_project(working_dir, remove_zip=False, logger=default_logger):
    if not isdir(working_dir):
        logger("project isn't a directory")
        return

    logger("Working folder:%s" % working_dir)
    
    # Create output directory (sibling 'complete' folder)
    abs_working = abspath(working_dir)
    parent_dir = dirname(abs_working)
    output_dir = join(parent_dir, 'complete')
    
    if not isdir(output_dir):
        try:
            makedirs(output_dir)
            logger("Created output directory: %s" % output_dir)
        except OSError:
            logger("Creation of output dir %s failed" % output_dir)
            return
    for f in sorted(listdir(working_dir)):
        if isfile(join(working_dir,f)):
            if f.endswith('zip'):
                m = re.search('(.*).txt.zip', f)
                if m is None:
                    continue
                extract_dir = join(working_dir, m.group(1))
                if not isdir(extract_dir):
                    try:
                        mkdir(extract_dir)
                    except OSError:
                        logger("Creation of dir %s failed" % extract_dir)
                        continue
                logger("Extracting %s to dir %s..." % (f, extract_dir))
                try:
                    zipref = zipfile.ZipFile(join(working_dir, f), 'r')
                    zipref.extractall(extract_dir)
                    zipref.close()
                except Exception as e:
                    logger("Unexpected error: %s %s" % (f, e))
                    # delete the extracted dir
                    if isdir(extract_dir):
                        rmtree(extract_dir)
                    continue
                
                # delete the zip file
                if remove_zip:
                    remove(join(working_dir, f))

    for f in sorted(listdir(working_dir)):
        if isdir(join(working_dir, f)):
            process_folder(working_dir, f, output_dir, remove_zip, logger)
    pass

def convert_to_md(working_dir, logger=default_logger):
    if not isdir(working_dir):
        logger("project isn't a directory")
        return

    # Determine output directory (sibling 'complete' folder)
    abs_working = abspath(working_dir)
    parent_dir = dirname(abs_working)
    output_dir = join(parent_dir, 'complete')

    if not isdir(output_dir):
        logger("Output directory %s does not exist. Please run processing first." % output_dir)
        return

    logger("Converting files in %s to Markdown..." % output_dir)
    
    txt_files = [f for f in sorted(listdir(output_dir)) if f.endswith('.txt')]
    
    if not txt_files:
        logger("No .txt files found in %s" % output_dir)
        return

    for f in txt_files:
        txt_path = join(output_dir, f)
        md_filename = f[:-4] + ".md"
        md_path = join(output_dir, md_filename)
        
        logger("Converting %s -> %s" % (f, md_filename))
        
        try:
            with open(txt_path, 'r', encoding='utf-8') as txt_file:
                content = txt_file.read()
            
            # Replace # with //
            new_content = content.replace('#', '//')
            
            with open(md_path, 'w', encoding='utf-8') as md_file:
                md_file.write(new_content)
                
            # Remove original txt file
            remove(txt_path)
            
        except Exception as e:
            logger("Error converting %s: %s" % (f, e))
            
    logger("Conversion completed.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = 'processing zip and combining txt files in it')
    parser.add_argument('project', help='Project directory path') # Changed to positional for backward compat if desired, or keep as named. Original was --project required=True.
    # Let's keep original args structure to be safe, but argparse usually handles --project.
    # The original code had: parser.add_argument('--project', required=True)
    # But the example usage in readme said: python process.py [path] OR python process.py --project [path]
    # Let's support both if possible, or just stick to the explicit one.
    # Actually, the original code ONLY supported --project. The readme example `python process.py project_folder` would fail with the original code unless it used sys.argv hack or I misread.
    # Wait, the original code:
    # parser.add_argument('--project', required=True)
    # So `python process.py project_folder` would definitely fail.
    # I will stick to the original argument structure to avoid breaking anything that relied on it, 
    # but I'll add a positional argument as a fallback or just keep it clean.
    
    # Re-reading original code:
    # parser.add_argument('--project', required=True)
    
    # I will modify it to accept a positional argument too, making it easier to use.
    parser = argparse.ArgumentParser(description = 'processing zip and combining txt files in it')
    parser.add_argument('--project', help='Project directory path')
    parser.add_argument('project_pos', nargs='?', help='Project directory path (positional)')
    parser.add_argument('--remove', action='store_true')
    parser.add_argument('--convert-md', action='store_true', help='Convert processed files to Markdown')
    args = parser.parse_args()

    project_dir = args.project or args.project_pos
    if not project_dir:
        parser.print_help()
        sys.exit(1)

    process_project(project_dir, args.remove)

    if args.convert_md:
        from process import convert_to_md # Import here or move function up if needed, but it's in same file
        convert_to_md(project_dir)


