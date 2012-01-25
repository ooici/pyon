'''
Created on Jan 4, 2012

@author: tomlennan
'''

import inspect
import os
import simplejson

import interface.objects
import interface.messages

def our_encoder(obj):
    obj_dict = obj.__dict__
    # Rmove special attributes added by gen code
    if "_svc_name" in obj_dict:
        del obj_dict["_svc_name"]
    if "_op_name" in obj_dict:
        del obj_dict["_op_name"]
    if "_schema" in obj_dict:
        del obj_dict["_schema"]
    return obj_dict

def main():
    classes = inspect.getmembers(interface.messages, inspect.isclass)
    json_output_text = ""
    for name, clzz in classes:
        if name != "IonObjectBase":
            clzz_instance = clzz()
            json_format = simplejson.dumps(clzz_instance, default=our_encoder)
            if name.endswith("_in"):
                json_output_text += "Service: " + clzz_instance._svc_name + "\n"
                json_output_text += "    Operation: " + clzz_instance._op_name + "\n"
                json_output_text += "        JSON input: " + str(json_format) + "\n"
            else:
                json_output_text += "        JSON output: " + str(json_format) + "\n"
                json_output_text += "\n"           

    outputdir = 'interface'
    json_examples_file = os.path.join(outputdir, 'json_examples.txt')
    try:
        os.unlink(json_examples_file)
    except:
        pass
    print "Writing sample json to '" + json_examples_file + "'"
    with open(json_examples_file, 'w') as f:
        f.write(json_output_text)

if __name__ == '__main__':
    main()
