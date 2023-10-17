#!/usr/bin/env python3
import sys
import logging
import argparse
from lxml import etree
from ncclient import manager
import os
import fnmatch

# Configure logging
logging.basicConfig(filename='/tmp/netconf.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

get_schemas = """
<filter xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
  <netconf-state xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
    <schemas/>
  </netconf-state>
</filter>
"""

module_name = "ietf-interfaces"
module_version = "2014-05-08"
get_schema_request = f"""
<rpc xmlns="urn:ietf:params:xml:ns:netconf:base:1.0" message-id="1">
    <get-schema xmlns="urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring">
        <identifier>{module_name}</identifier>
        <version>{module_version}</version>
    </get-schema>
</rpc>
"""

class NcTools():
    def __init__(self):
        self.yang_directory = "/tmp/yang"
        self.schema = "ietf-interfaces.yang"

    def get_schema(self, m, modname):
        schema = m.get_schema(modname)
        return schema

    def create_yang_dir(self):
        try:
            os.makedirs(self.yang_directory)
        except:
            pass
        if not os.path.exists(self.yang_directory):
            raise NotADirectoryError
        
    def mark_yang_file(self, modname):
        yang_file_name = self.yang_directory + "/" + modname + ".yang.yes"
        with open(yang_file_name, "w") as m:
            m.write("")
            m.close()

    def get_list_of_schema(self, m):
        # Create directory to store the list of schemas
        self.create_yang_dir()
        # Send the RPC operation to get the schema.
        result_string = m.get(filter=get_schemas).xml.encode()
        logging.info (f"Output is: %s", type(result_string))

        # Parse the XML string
        xml_tree = etree.fromstring(result_string)

        # Find and extract the schema elements
        schema_elements = xml_tree.xpath("//nc:schema", namespaces={"nc": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"})

        skipped_count = 0
        marked_count = 0
        # Process and print the extracted schema information
        for schema_element in schema_elements:
            identifier = schema_element.find("nc:identifier", namespaces={"nc": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"}).text
            version = schema_element.find("nc:version", namespaces={"nc": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"}).text
            format_ = schema_element.find("nc:format", namespaces={"nc": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"}).text
            namespace = schema_element.find("nc:namespace", namespaces={"nc": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"}).text
            location = schema_element.find("nc:location", namespaces={"nc": "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring"}).text
            yang_file_name = self.directory + "/" + identifier + ".yang"
            if os.path.exists(yang_file_name):
                skipped_count += 1
                continue
            self.mark_yang_file(identifier)
            marked_count += 1

        logging.debug("Model list fetched.")
        logging.info("Marked %d modules for download, skipped %d", marked_count, skipped_count)
        print(f"Marked {marked_count} modules for download, skipped {skipped_count}")

    def list_models_in_yang_dir(self, cat='enabled'):
        if(cat == 'marked'):
            return [f[:-9] for f in os.listdir(self.yang_directory) if fnmatch.fnmatch(f, '*.yang.yes')]
        if(cat == 'disabled'):
            return [f[:-8] for f in os.listdir(self.yang_directory) if fnmatch.fnmatch(f, '*.yang.no')]
        if(cat == 'enabled'):
            return [f[:-5] for f in os.listdir(self.yang_directory) if fnmatch.fnmatch(f, '*.yang')]
        if(cat == 'builtin'):
            return [f[:-5] for f in os.listdir(self.ncs_dir + "/src/ncs/yang") if fnmatch.fnmatch(f, '*.yang')]
        return []

    def download_models_in_yang_dir(self, m):
        model_list = self.list_models_in_yang_dir('marked')
        logging.debug(model_list)

        files_total = len(model_list)
        if 0 == files_total:
            return {'yang-directory':self.yang_directory,
                    'error':"No files marked for download; did you forget to run --list for all the files"}
        downloaded_count = 0
        failed_count = 0
        skipped_count = 0
        file_no = 0
        result_str = ""
        for modname in model_list:
            file_no += 1
            yang_file_name = self.yang_directory + "/" + modname + ".yang"
            logging.debug("Checking " + yang_file_name)
            if os.path.exists(yang_file_name) or os.path.exists(yang_file_name + ".no"):
                skipped_count += 1
                logging.debug("Module already downloaded, skipping " + modname)
                print("Module {modname} already downloaded, skipping".format(modname=modname))
                continue
            logging.debug("Downloading module " + modname)
            print ("Downloading module {0}, {1}/{2}".format(modname, file_no, files_total))
            try:
                xml_module = self.get_schema(m, modname)
                logging.debug("Downloaded schema for " + modname)
                print("Downloaded schema for {modname}".format(modname=modname))
            except Exception as e:
                logging.debug("Download failed")
                result_str += "Failed {0} fetch error '{1}'\n".format(modname, repr(e))
                failed_count += 1
            else:
                try:
                    logging.info("Writing model " + modname + " to " + yang_file_name)
                    print("Writing model {modname} to {yang_file_name}".format(modname=modname, yang_file_name=yang_file_name))
                    with open(yang_file_name, "w") as fd:
                        fd.write(str(xml_module))
                        logging.info("Wrote model " + modname + " to " + yang_file_name)
                        print("Wrote {modname} to {yang_file_name}".format(modname=modname, yang_file_name=yang_file_name))
                        fd.close()
                except Exception as e:
                # Handle the exception, e.g., print an error message
                    print(f"Error writing to file: {e}")
                    logging.debug("Downloaded module " + modname)
                    result_str += "Downloaded {0}\n".format(modname)
                    downloaded_count += 1
                    if os.path.exists(yang_file_name + ".yes"):
                        os.remove(yang_file_name + ".yes")
                except:
                    logging.debug("Writing failed")
                    result_str += "Failed {0} write error\n".format(modname)
                    failed_count += 1
        
        logging.debug("Model download done")
        message = "Downloaded {0} modules, failed {1}, skipped {2}:\n{3}".format(
            downloaded_count, failed_count, skipped_count, result_str)
        return {'yang-directory':self.yang_directory, 'message':message}
    
def parse_args(sys_args):
    usage = """
    %nctools [-h | --help] [options]

    One of the options must be given.
    """

    # Create an instance of the parser
    parser = argparse.ArgumentParser(description=usage)
    parser.add_argument("-u", "--user", dest="username", default="root",
                      help="username")
    parser.add_argument("-p", "--password", dest="password", default="arrcus",
                      help="password")
    parser.add_argument("--host", dest="host", default="localhost",
                      help="NETCONF server hostname")
    parser.add_argument("--port", type=int, dest="port", default=830,
                      help="NETCONF server SSH port")
    parser.add_argument("-l", "--list", action='store_true',
                        help="Get a list of schemas supported")
    parser.add_argument("-d", "--dir", default="/tmp/yang",
                        help="Directory to store the list of schemas")
    parser.add_argument("--download", action='store_true',
                        help="Download the list of YANG models")
    parser.add_argument("--schema", dest="schema", default="ietf-interfaces.yang",
                        action='store_true', help="Download the given schema")
    args = parser.parse_args()
    return (args)

def main(sys_args, ncTools, logger=None):
    args = parse_args(sys_args)
    if args.dir:
        ncTools.directory=args.dir
    if args.schema:
        ncTools.schema=args.schema


    if logger:
        logger.debug("nctools.py: about to connect")

    try:
        with manager.connect(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            device_params={"name": "default"},
            allow_agent=False,
            look_for_keys=False,
            hostkey_verify=False,
        ) as m:
            if args.list:
                ncTools.get_list_of_schema(m)
            if args.download:
                ncTools.download_models_in_yang_dir(m)
            if args.schema:
                ncTools.get_schema(m, "openconfig-interfaces")
    except Exception as e:
      print("An error occurred:", str(e))

if __name__ == "__main__":
    ncTools = NcTools()

    main(sys.argv[1:], ncTools)
