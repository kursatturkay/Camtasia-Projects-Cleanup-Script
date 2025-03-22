#!/usr/bin/env python
"""
Camtasia Project Cleanup Script

This script searches for unused files in Camtasia projects (.tscproj files) and optionally
moves them to the trash. It can process a single project or recursively search through directories.

Example Usage:
    # Show unused .trec files in a single project (without deleting)
    python cleanup_trec.py "D:\Projects\MyProject.tscproj"
    
    # Send unused .trec files to trash for a single project
    python cleanup_trec.py "D:\Projects\MyProject.tscproj" --sendtotrash
    
    # List all files used in a project
    python cleanup_trec.py "D:\Projects\MyProject.tscproj" --list-used
    
    # Show all unused files (not just .trec)
    python cleanup_trec.py "D:\Projects\MyProject.tscproj" --all-unused
    
    # Process all projects in a directory and subdirectories
    python cleanup_trec.py "D:\Projects" --recursive
    
    # Clean up all unused files in all projects recursively
    python cleanup_trec.py "D:\Projects" --recursive --all-unused --sendtotrash
    
    # Clean all projects and show what files are kept
    python cleanup_trec.py "D:\Projects" --recursive --list-used --all-unused --sendtotrash

Requirements:
    - Python 3.6+
    - send2trash package: pip install send2trash
"""

import os
import json
import send2trash
import argparse

def get_referenced_trec_files(tscproj_path):
    """Extract all referenced .trec files from a tscproj file"""
    try:
        with open(tscproj_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        referenced_trec_files = set()
        
        # Process source bin entries
        if 'sourceBin' in data:
            for source in data['sourceBin']:
                if 'src' in source:
                    src_file = source['src']
                    if src_file.lower().endswith('.trec'):
                        referenced_trec_files.add(src_file)
                
                # Check sourceTracks for additional metadata
                if 'sourceTracks' in source:
                    for track in source['sourceTracks']:
                        if 'metaData' in track:
                            # Some metaData entries may contain semicolon-separated filenames
                            metadata = track['metaData']
                            if isinstance(metadata, str) and ';' in metadata:
                                files = metadata.split(';')
                                for file in files:
                                    if file.strip() and file.strip().lower().endswith('.trec'):
                                        referenced_trec_files.add(file.strip())
        
        return referenced_trec_files
        
    except Exception as e:
        print(f"Error processing {tscproj_path}: {str(e)}")
        return set()

def process_directory_or_file(path, dry_run=True, all_unused=False, list_used=False):
    """Process a single tscproj file and clean up unreferenced .trec files"""
    # Check if the path is a directory
    if os.path.isdir(path):
        directory = path
        
        # Look for a tscproj file with the same name as the directory
        dir_name = os.path.basename(os.path.normpath(directory))
        potential_tscproj = os.path.join(directory, dir_name)
        
        # If there's no extension, add it
        if not potential_tscproj.lower().endswith('.tscproj'):
            potential_tscproj += '.tscproj'
            
        if os.path.isfile(potential_tscproj):
            tscproj_path = potential_tscproj
            print(f"Found matching tscproj file: {os.path.basename(tscproj_path)}")
        else:
            # Look for any tscproj file in the directory
            tscproj_files = [f for f in os.listdir(directory) if f.lower().endswith('.tscproj')]
            if tscproj_files:
                tscproj_path = os.path.join(directory, tscproj_files[0])
                print(f"Using first tscproj file found: {os.path.basename(tscproj_path)}")
            else:
                print(f"Error: No .tscproj file found in {directory}")
                return False
    
    # Check if the path is a file
    elif os.path.isfile(path):
        if not path.lower().endswith('.tscproj'):
            print(f"Error: {path} is not a .tscproj file")
            return False
        tscproj_path = path
        directory = os.path.dirname(tscproj_path)
    
    else:
        print(f"Error: {path} is not a valid directory or file")
        return False
    
    print(f"Processing project file: {os.path.basename(tscproj_path)}")
    print(f"Looking for unused .trec files in directory: {directory}")
    
    # Collect all relevant files in the directory
    all_trec_files = set()
    all_files = set()
    referenced_files = set()
    
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)
        if os.path.isfile(file_path):
            all_files.add(file)
            if file.lower().endswith('.trec'):
                all_trec_files.add(file)
    
    if not all_trec_files and not all_unused:
        print(f"No .trec files found in {directory}")
        return True
    
    # Get referenced files from project
    referenced_trec_files = get_referenced_trec_files(tscproj_path)
    
    # Get all referenced files (not just .trec)
    try:
        with open(tscproj_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if 'sourceBin' in data:
            for source in data['sourceBin']:
                if 'src' in source:
                    referenced_files.add(source['src'])
                    
                # Check sourceTracks for additional metadata
                if 'sourceTracks' in source:
                    for track in source['sourceTracks']:
                        if 'metaData' in track:
                            metadata = track['metaData']
                            if isinstance(metadata, str) and ';' in metadata:
                                files = metadata.split(';')
                                for file in files:
                                    if file.strip():
                                        referenced_files.add(file.strip())
    except Exception as e:
        print(f"Error extracting all referenced files: {str(e)}")
    
    # Always keep the tscproj file itself
    tscproj_filename = os.path.basename(tscproj_path)
    referenced_files.add(tscproj_filename)
    
    # If we're just listing used files, do that and return
    if list_used:
        print(f"Files used in project {tscproj_filename}:")
        for file in sorted(referenced_files):
            if os.path.isfile(os.path.join(directory, file)):
                print(f"  {file}")
            else:
                print(f"  {file} (referenced but not found in directory)")
        return True
    
    # Files to be deleted
    if all_unused:
        # All files except referenced ones and json files
        files_to_delete = set()
        for file in all_files:
            if file not in referenced_files and not file.lower().endswith('.json'):
                files_to_delete.add(file)
    else:
        # Only unreferenced .trec files
        files_to_delete = all_trec_files - referenced_trec_files
    
    # Delete or report files
    if not files_to_delete:
        if all_unused:
            print(f"No unused files found in {directory}")
        else:
            print(f"No unused .trec files found in {directory}")
    else:
        if all_unused:
            print(f"Found {len(files_to_delete)} unused files in {directory}:")
        else:
            print(f"Found {len(files_to_delete)} unused .trec files in {directory}:")
            
        for file in sorted(files_to_delete):
            file_path = os.path.join(directory, file)
            if dry_run:
                print(f"Would send to trash: {file}")
            else:
                try:
                    print(f"Sending to trash: {file}")
                    send2trash.send2trash(file_path)
                except Exception as e:
                    print(f"Error sending {file} to trash: {str(e)}")
    
    return True

def process_recursively(base_path, dry_run, all_unused, list_used):
    """Recursively find and process all .tscproj files in subdirectories"""
    processed_count = 0
    
    # If the path is directly a file, just process it
    if os.path.isfile(base_path) and base_path.lower().endswith('.tscproj'):
        if process_directory_or_file(base_path, dry_run, all_unused, list_used):
            processed_count += 1
        return processed_count
    
    # If it's a directory, walk through it recursively
    for root, dirs, files in os.walk(base_path):
        tscproj_files = [f for f in files if f.lower().endswith('.tscproj')]
        
        for tscproj_file in tscproj_files:
            tscproj_path = os.path.join(root, tscproj_file)
            print(f"\n{'='*60}\nProcessing: {tscproj_path}\n{'='*60}")
            if process_directory_or_file(tscproj_path, dry_run, all_unused, list_used):
                processed_count += 1
    
    if processed_count == 0:
        print(f"No .tscproj files found in {base_path} or its subdirectories")
    
    return processed_count

def main():
    parser = argparse.ArgumentParser(description='Clean up unused .trec files in Camtasia project files')
    parser.add_argument('path', help='Path to a directory containing a .tscproj file or to the .tscproj file itself')
    parser.add_argument('--sendtotrash', action='store_true', help='Send unused files to trash (otherwise just report)')
    parser.add_argument('--all-unused', action='store_true', help='Send all unused files (not just .trec files) to trash')
    parser.add_argument('--list-used', action='store_true', help='List all files used in the project')
    parser.add_argument('--recursive', action='store_true', help='Recursively process all .tscproj files in subdirectories')
    
    args = parser.parse_args()
    
    if args.recursive:
        print(f"Starting recursive processing in {args.path}")
        count = process_recursively(args.path, dry_run=not args.sendtotrash, all_unused=args.all_unused, list_used=args.list_used)
        print(f"\nProcessed {count} .tscproj files recursively")
    else:
        process_directory_or_file(args.path, dry_run=not args.sendtotrash, all_unused=args.all_unused, list_used=args.list_used)

if __name__ == "__main__":
    main()