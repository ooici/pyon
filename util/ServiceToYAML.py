'''
Created on Sep 7, 2011

@author: tomlennan
'''

import os

if __name__ == '__main__':
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.find('__init__.py') == -1 and file.find('ServiceToYAML.py') == -1 and file.find('.py') != -1 and file.find('.pyc') == -1:
                f = open(os.path.join(root, file), 'r')
                lines = f.readlines()
                f.close()
            
                # Determine if service class
                isService = False
                for line in lines:
                    if line.find('(ServiceProcess)') != -1:
                        isService = True
                        break
                outlines = []
                if isService:
                    for line in lines:
                        if line.find('def op_') != -1:
                            startIndex = line.find('def op_') + 7
                            endIndex = line.find('(')
                            opName = line[startIndex:endIndex] + ":\n\n"
                            outlines.append(opName)
                    # Is a service class, create interface YAML
                    filenameBase = file[0:file.find('.py')]
                    f = open("tmp/" + filenameBase + ".yml", 'w')
                    for outline in outlines:
                        f.write(outline)
                    f.close()
            
            