'''
Created on Sep 7, 2011

@author: tomlennan
'''

import os

if __name__ == '__main__':
    protodef_dir = str(os.getcwd()) + "/../../protodefs/by_id"
    output_dir = str(os.getcwd()) + "/../../servicedefs/"
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
                    # Look for proto buff definitions
                    for line in lines:
                        if line.find('object_utils.create_type_identifier(object_id=') != -1:
                            startIndex = line.find('object_utils.create_type_identifier(object_id=') + 46
                            endIndex = line.find(',')
                            protobuff_id = line[startIndex:endIndex]
                            protobuff_id.replace(' ', '')
                            # Read proto buff definition into outlines so they will be
                            # appended above the service definitions
                            gpbfile = open(os.path.join(protodef_dir, protobuff_id + ".yml"), 'r')
                            for gpbfile_line in gpbfile.readlines():
                                outlines.append(gpbfile_line)
                            gpbfile.close()
                            outlines += "\n\n"

                    # Add name and dependencies tags
                    outlines.append("name: " + file + "\n")
                    outlines.append("dependencies: []\n")
                    outlines.append("methods:\n")

                    # Look for op definitions                    
                    for line in lines:
                        if line.find('def op_') != -1:
                            startIndex = line.find('def op_') + 7
                            endIndex = line.find('(')
                            opName = line[startIndex:endIndex] + ":\n"
                            outlines.append("  " + opName)
                            outlines.append("    in:\n\n")
                            outlines.append("    out:\n\n")
                    # Is a service class, create interface YAML
                    filenameBase = file[0:file.find('.py')]
                    f = open(output_dir + filenameBase + ".yml", 'w')
                    for outline in outlines:
                        f.write(outline)
                    f.close()
            
            