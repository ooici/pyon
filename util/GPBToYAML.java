package ion.util;

import ion.core.IonBootstrap;

import java.io.FileOutputStream;
import java.io.PrintStream;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;

import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;

import com.google.protobuf.ByteString;
import com.google.protobuf.GeneratedMessage;
import com.google.protobuf.JsonFormat;
import com.google.protobuf.Message;
import com.google.protobuf.Message.Builder;

public class GPBToYAML {

    public Builder getMessageBuilder(Class clazz) throws SecurityException, NoSuchMethodException, IllegalArgumentException, IllegalAccessException, InvocationTargetException {
		// Get GeneratedMessage class for type id
    	if (clazz == null) {
    		System.out.println("Could not find GPB class");
    		return null;
    	}

		// Get builder instance by invoking static newBuilder() via reflection
		Method method = clazz.getMethod("newBuilder", (Class[])null);
		Message.Builder builder = (Message.Builder)method.invoke(null, (Object[])null);

		return builder;
    }

    public void convertGPB(Builder builder) throws IllegalArgumentException, IllegalAccessException, InvocationTargetException, SecurityException, NoSuchMethodException {
		Class clazz = builder.getClass();
		Method[] methods = clazz.getMethods();
		for (int j = 0; j < methods.length; j++) {
			if (methods[j].getName().startsWith("set") && (!methods[j].getName().equals("setUnknownFields"))) {
				Class[] parameters = methods[j].getParameterTypes();
				if (parameters.length == 1) {
					Object[] inputParam = new Object[1];
					if (parameters[0] == String.class) {
						inputParam[0] = "";
					}
					else if (parameters[0] == int.class) {
						inputParam[0] = new Integer(-1);
					}
					else if (parameters[0] == double.class) {
						inputParam[0] = new Double(-1.1);
					}
					else if (parameters[0] == long.class) {
						inputParam[0] = new Long(-1);
					}
					else if (parameters[0] == float.class) {
						inputParam[0] = new Float(-1);
					}
					else if (parameters[0] == boolean.class) {
						inputParam[0] = new Boolean(true);
					}
					else if (parameters[0] == ByteString.class) {
						inputParam[0] = ByteString.copyFromUtf8("");
					}
					else if (parameters[0].getSuperclass() == GeneratedMessage.class) {
						continue;
					}
					else if (parameters[0].getSuperclass() == GeneratedMessage.Builder.class) {
						Class parentClazz = parameters[0].getEnclosingClass();
						Method method = parentClazz.getMethod("newBuilder", (Class[])null);
						Message.Builder subBuilder = (Message.Builder)method.invoke(null, (Object[])null);
						convertGPB(subBuilder);
						inputParam[0] = subBuilder;
					}
					else {
						Class inputParamClazz = (Class)parameters[0];
						Method[] inputParamClazzMethods = inputParamClazz.getMethods();
						boolean found = false;
						for (int k = 0; k < inputParamClazzMethods.length; k++) {
							if (inputParamClazzMethods[k].getName().equals("values")) {
								Object[] values = (Object[])inputParamClazzMethods[k].invoke(null, (Object[])null);
								inputParam[0] = values[0];
								found = true;
								break;
							}
						}
						assert (found);
					}
					methods[j].invoke(builder, inputParam);
				}
			}
			else if (methods[j].getName().startsWith("add") && (!methods[j].getName().startsWith("addAll"))) {
				Class[] parameters = methods[j].getParameterTypes();
				if (parameters.length == 1) {
					if (parameters[0].getSimpleName().equals("Builder")) {
						Object[] inputParam = new Object[1];
						Class inputParamClazz = (Class)parameters[0];
						Class parentClazz = inputParamClazz.getEnclosingClass();
						Method method = parentClazz.getMethod("newBuilder", (Class[])null);
						Message.Builder subBuilder = (Message.Builder)method.invoke(null, (Object[])null);
						convertGPB(subBuilder);
						inputParam[0] = subBuilder;
						methods[j].invoke(builder, inputParam);
					}
				}
			}
		}
    }
    
    /**
     * Routine that takes JSON and converts it to YAML format
     */
    public String convertJSONToYAML(int msgId, int msgVersion, String jsonString, String className) {
    	String yamlString = "# _ID = " + msgId + "\n";
    	yamlString += "# _VERSION = " + msgVersion + "\n";
    	yamlString += "obj:\n";
    	
    	yamlString += "  " + className + ":";
    	
    	// Walk the string character by character
    	int indent = 1;
    	for (int i = 0; i < jsonString.length(); i++) {
    		char c = jsonString.charAt(i);
    		
    		switch (c) {
    		case '{':
    			yamlString += "\n";
    			indent++;
    			for (int j = 0; j < indent; j++) {
    				yamlString += "  ";
    			}
    			break;

    		case '}':
    			indent--;
    			break;

    		case ',':
    			yamlString += "\n";
    			for (int j = 0; j < indent; j++) {
    				yamlString += "  ";
    			}
    			break;

    		case '"':
    			// Peek ahead and see if empty string
    			if (jsonString.charAt(i+1) == '"') {
    				i++;
    				yamlString += "\"\"";
    			}
    			break;

    		default:
    			yamlString += c;
    			break;
    		}
    	}
    	
    	yamlString += "\n--- # _ID = " + msgId;
    	
    	return yamlString;
    }

    /**
     * Main method will produce a series of yaml files describing data types.
     * @param args
     */
	public static void main(String[] args) {
		GPBToYAML gpbToYAML = new GPBToYAML();
		
		Collection<Class> gpbClasses = IonBootstrap.getValueSet();

		try {
			for (Class clazz : gpbClasses) {
				Builder builder = gpbToYAML.getMessageBuilder(clazz);
				gpbToYAML.convertGPB(builder);
				int msgId = IonBootstrap.getKeyValueForMappedClass(clazz);
				int msgVersion = IonBootstrap.getMappedClassVersion(msgId);
				String jsonString = JsonFormat.printToString(builder.build());
				String yamlString = gpbToYAML.convertJSONToYAML(msgId, msgVersion, jsonString, clazz.getSimpleName());

				FileOutputStream out = new FileOutputStream("../protodefs/by_name/" + clazz.getSimpleName() + ".yml");
				PrintStream p = new PrintStream(out);
				p.print(yamlString);
				p.close();
				out = new FileOutputStream("../protodefs/by_id/" + msgId + ".yml");
				p = new PrintStream(out);
				p.print(yamlString);
				p.close();
			}
		}
		catch (Exception e) {
			System.out.println("Exception: " + e);
		}
	}

}
