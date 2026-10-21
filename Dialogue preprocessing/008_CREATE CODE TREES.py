import os
import ast
import re

def turn_code_into_tree(folder):
    python_files_in_folder = [f for f in os.listdir(folder) if f.endswith('.py')]
    print("folder",python_files_in_folder)
    for python_file in python_files_in_folder:
        print("file", python_file)
        tree_filename = python_file[:-3] + "_tree.txt"
        full_file_path = os.path.join(folder, python_file)
        tree_file_path = os.path.join(folder, tree_filename)
        with open(full_file_path, 'r') as f:
            code_list = [] #List to store each line of code
            indented_list = [] #List to store indented bits before appending to main list
            code_readlines = f.readlines()

            #Filling up list of code lines
            for line in iter(code_readlines):
                #If the current line belongs to and indented bit, put it in special list
                if bool(re.search(":$", line)) == True or bool(re.search("^   ", line)) == True: 
                    indented_list.append(line)
                #If this is the end of the indented bit, append special list to main list as one string
                if bool(re.search(":$", next(iter(code_readlines)))) == False and bool(re.search("^   ", next(iter(code_readlines)))) == False:
                    code_list.append(str(indented_list))
                #Independent code statements
                else:
                #Empty the list of indented bits - we're outide a function/etc. now
                    indented_list = []  
                    code_list.append(line)


            #Returning tree in string format
            whole_tree_string = ""
            for codeline in code_list:
                codeline_string = str(codeline)
                #Try because the parser raises errors for any code that has bad syntax/is incomplete
                try:
                    tree_string = ast.parse(codeline_string)
                    if len(whole_tree_string) > 0:
                        whole_tree_string = whole_tree_string + "\n" + ast.dump(tree_string)
                    else:
                        whole_tree_string = ast.dump(tree_string)
                except:
                    pass
            print(whole_tree_string, file=open(tree_file_path, "w"))
    return print("done") #print(whole_tree_string, file=open(tree_file_path, "w"))

if __name__ == "__main__":
	code_folder = 'path/to/code/folder' # Replace with the actual path to your code folder
	turn_code_into_tree(code_folder)
