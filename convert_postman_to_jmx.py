#!/usr/bin/env python3
"""
Postman Collection to JMeter JMX Converter
Converts Postman collection JSON files to JMeter JMX format
Supports: headers, params, body, folders, environment variables, and basic assertions
"""

import json
import sys
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Any, Optional
import argparse
import re


class PostmanToJMeterConverter:
    def __init__(self):
        self.jmx_root = None
        self.test_plan = None
        self.thread_group = None
        self.hash_tree = None
        self.env_vars = {}
        
    def create_jmx_structure(self, collection_name: str):
        """Create the basic JMX structure"""
        self.jmx_root = ET.Element('jmeterTestPlan', {
            'version': '1.2',
            'properties': '5.0',
            'jmeter': '5.6.3'
        })
        
        # Create main hashtree
        self.hash_tree = ET.SubElement(self.jmx_root, 'hashTree')
        
        # Create Test Plan inside hashtree
        self.test_plan = ET.SubElement(self.hash_tree, 'TestPlan', {
            'guiclass': 'TestPlanGui',
            'testclass': 'TestPlan',
            'testname': collection_name,
            'enabled': 'true'
        })
        
        ET.SubElement(self.test_plan, 'stringProp', {'name': 'TestPlan.comments'})
        ET.SubElement(self.test_plan, 'boolProp', {'name': 'TestPlan.functional_mode'}).text = 'false'
        ET.SubElement(self.test_plan, 'boolProp', {'name': 'TestPlan.serialize_threadgroups'}).text = 'false'
        
        # Element properties
        element_prop = ET.SubElement(self.test_plan, 'elementProp', {
            'name': 'TestPlan.user_defined_variables',
            'elementType': 'Arguments',
            'guiclass': 'ArgumentsPanel',
            'testclass': 'Arguments',
            'testname': 'User Defined Variables',
            'enabled': 'true'
        })
        ET.SubElement(element_prop, 'collectionProp', {'name': 'Arguments.arguments'})
        
        ET.SubElement(self.test_plan, 'stringProp', {'name': 'TestPlan.user_define_classpath'})
        
        # Create sub hashtree for test elements
        self.sub_hash_tree = ET.SubElement(self.hash_tree, 'hashTree')
        
    def add_thread_group(self, name: str = "Thread Group"):
        """Add a thread group to the test plan"""
        thread_group = ET.SubElement(self.sub_hash_tree, 'ThreadGroup', {
            'guiclass': 'ThreadGroupGui',
            'testclass': 'ThreadGroup',
            'testname': name,
            'enabled': 'true'
        })
        
        ET.SubElement(thread_group, 'stringProp', {'name': 'ThreadGroup.on_sample_error'}).text = 'continue'
        
        # Thread properties
        loop_controller = ET.SubElement(thread_group, 'elementProp', {
            'name': 'ThreadGroup.main_controller',
            'elementType': 'LoopController',
            'guiclass': 'LoopControlPanel',
            'testclass': 'LoopController',
            'testname': 'Loop Controller',
            'enabled': 'true'
        })
        ET.SubElement(loop_controller, 'boolProp', {'name': 'LoopController.continue_forever'}).text = 'false'
        ET.SubElement(loop_controller, 'stringProp', {'name': 'LoopController.loops'}).text = '1'
        
        ET.SubElement(thread_group, 'stringProp', {'name': 'ThreadGroup.num_threads'}).text = '1'
        ET.SubElement(thread_group, 'stringProp', {'name': 'ThreadGroup.ramp_time'}).text = '1'
        ET.SubElement(thread_group, 'longProp', {'name': 'ThreadGroup.start_time'}).text = '0'
        ET.SubElement(thread_group, 'longProp', {'name': 'ThreadGroup.end_time'}).text = '0'
        ET.SubElement(thread_group, 'boolProp', {'name': 'ThreadGroup.scheduler'}).text = 'false'
        ET.SubElement(thread_group, 'stringProp', {'name': 'ThreadGroup.duration'}).text = ''
        ET.SubElement(thread_group, 'stringProp', {'name': 'ThreadGroup.delay'}).text = ''
        
        self.thread_group = ET.SubElement(self.sub_hash_tree, 'hashTree')
        
        return self.thread_group
    
    def load_environment(self, env_file: str):
        """Load Postman environment variables"""
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                env_data = json.load(f)
                if 'values' in env_data:
                    for item in env_data['values']:
                        if item.get('enabled', True):
                            self.env_vars[item['key']] = item['value']
        except Exception as e:
            print(f"Warning: Could not load environment file: {e}")
    
    def replace_variables(self, text: str) -> str:
        """Replace Postman variables {{var}} with JMeter ${var} format"""
        if not text:
            return text
        
        # Replace {{variable}} with ${variable}
        result = re.sub(r'\{\{([^}]+)\}\}', r'${\1}', text)
        return result
    
    def parse_url(self, request: Dict) -> tuple:
        """Parse Postman URL into protocol, host, port, path"""
        url = request.get('url', {})
        
        if isinstance(url, str):
            # Simple string URL
            url_str = self.replace_variables(url)
            if '://' in url_str:
                protocol = url_str.split('://')[0]
                remaining = url_str.split('://')[1]
            else:
                protocol = 'https'
                remaining = url_str
            
            if '/' in remaining:
                host_port = remaining.split('/')[0]
                path = '/' + '/'.join(remaining.split('/')[1:])
            else:
                host_port = remaining
                path = '/'
            
            if ':' in host_port and not host_port.startswith('['):
                host = host_port.split(':')[0]
                port = host_port.split(':')[1]
            else:
                host = host_port
                port = '443' if protocol == 'https' else '80'
            
            return protocol, host, port, path
        
        # Object format
        protocol = url.get('protocol', 'https')
        host_parts = url.get('host', [])
        host = '.'.join(host_parts) if isinstance(host_parts, list) else str(host_parts)
        port = str(url.get('port', '443' if protocol == 'https' else '80'))
        path_parts = url.get('path', [])
        path = '/' + '/'.join(path_parts) if path_parts else '/'
        
        # Apply variable replacement
        host = self.replace_variables(host)
        path = self.replace_variables(path)
        
        # Handle query parameters
        query = url.get('query', [])
        if query:
            query_string = '&'.join([f"{q['key']}={self.replace_variables(q.get('value', ''))}" 
                                     for q in query if q.get('disabled') != True])
            if query_string:
                path += '?' + query_string
        
        return protocol, host, port, path
    
    def add_http_sampler(self, parent: ET.Element, item: Dict, name: str):
        """Add HTTP Request sampler"""
        request = item.get('request', {})
        
        # Parse URL
        protocol, host, port, path = self.parse_url(request)
        method = request.get('method', 'GET')
        
        # Create HTTP Sampler
        sampler = ET.SubElement(parent, 'HTTPSamplerProxy', {
            'guiclass': 'HttpTestSampleGui',
            'testclass': 'HTTPSamplerProxy',
            'testname': name,
            'enabled': 'true'
        })
        
        # Add properties
        ET.SubElement(sampler, 'elementProp', {
            'name': 'HTTPsampler.Arguments',
            'elementType': 'Arguments',
            'guiclass': 'HTTPArgumentsPanel',
            'testclass': 'Arguments',
            'testname': 'User Defined Variables',
            'enabled': 'true'
        })
        
        arguments = ET.SubElement(sampler, 'elementProp', {
            'name': 'HTTPsampler.Arguments',
            'elementType': 'Arguments'
        })
        args_collection = ET.SubElement(arguments, 'collectionProp', {'name': 'Arguments.arguments'})
        
        # Handle body
        body = request.get('body', {})
        if body:
            mode = body.get('mode', 'raw')
            
            if mode == 'raw':
                raw_data = self.replace_variables(body.get('raw', ''))
                ET.SubElement(sampler, 'boolProp', {'name': 'HTTPSampler.postBodyRaw'}).text = 'true'
                arg = ET.SubElement(args_collection, 'elementProp', {
                    'name': '',
                    'elementType': 'HTTPArgument'
                })
                ET.SubElement(arg, 'boolProp', {'name': 'HTTPArgument.always_encode'}).text = 'false'
                ET.SubElement(arg, 'stringProp', {'name': 'Argument.value'}).text = raw_data
                ET.SubElement(arg, 'stringProp', {'name': 'Argument.metadata'}).text = '='
            
            elif mode == 'formdata' or mode == 'urlencoded':
                form_data = body.get(mode, [])
                for param in form_data:
                    if param.get('disabled') != True:
                        arg = ET.SubElement(args_collection, 'elementProp', {
                            'name': param['key'],
                            'elementType': 'HTTPArgument'
                        })
                        ET.SubElement(arg, 'boolProp', {'name': 'HTTPArgument.always_encode'}).text = 'true'
                        ET.SubElement(arg, 'stringProp', {'name': 'Argument.value'}).text = self.replace_variables(param.get('value', ''))
                        ET.SubElement(arg, 'stringProp', {'name': 'Argument.metadata'}).text = '='
                        ET.SubElement(arg, 'boolProp', {'name': 'HTTPArgument.use_equals'}).text = 'true'
                        ET.SubElement(arg, 'stringProp', {'name': 'Argument.name'}).text = param['key']
        
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.domain'}).text = host
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.port'}).text = port
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.protocol'}).text = protocol
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.contentEncoding'})
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.path'}).text = path
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.method'}).text = method
        ET.SubElement(sampler, 'boolProp', {'name': 'HTTPSampler.follow_redirects'}).text = 'true'
        ET.SubElement(sampler, 'boolProp', {'name': 'HTTPSampler.auto_redirects'}).text = 'false'
        ET.SubElement(sampler, 'boolProp', {'name': 'HTTPSampler.use_keepalive'}).text = 'true'
        ET.SubElement(sampler, 'boolProp', {'name': 'HTTPSampler.DO_MULTIPART_POST'}).text = 'false'
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.embedded_url_re'})
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.connect_timeout'})
        ET.SubElement(sampler, 'stringProp', {'name': 'HTTPSampler.response_timeout'})
        
        # Create sampler hashtree
        sampler_tree = ET.SubElement(parent, 'hashTree')
        
        # Add headers
        headers = request.get('header', [])
        if headers:
            header_manager = ET.SubElement(sampler_tree, 'HeaderManager', {
                'guiclass': 'HeaderPanel',
                'testclass': 'HeaderManager',
                'testname': 'HTTP Header Manager',
                'enabled': 'true'
            })
            
            headers_collection = ET.SubElement(header_manager, 'collectionProp', {'name': 'HeaderManager.headers'})
            
            for header in headers:
                if header.get('disabled') != True:
                    header_elem = ET.SubElement(headers_collection, 'elementProp', {
                        'name': '',
                        'elementType': 'Header'
                    })
                    ET.SubElement(header_elem, 'stringProp', {'name': 'Header.name'}).text = header['key']
                    ET.SubElement(header_elem, 'stringProp', {'name': 'Header.value'}).text = self.replace_variables(header.get('value', ''))
            
            ET.SubElement(sampler_tree, 'hashTree')
        
        # Add basic assertions if response tests exist
        events = item.get('event', [])
        for event in events:
            if event.get('listen') == 'test':
                script = event.get('script', {})
                exec_lines = script.get('exec', [])
                
                for line in exec_lines:
                    # Simple response code assertion
                    if 'pm.response.to.have.status(200)' in line or 'response.code === 200' in line:
                        self.add_response_assertion(sampler_tree, '200', 'Response Code')
                    elif 'pm.response.to.be.ok' in line:
                        self.add_response_assertion(sampler_tree, '200', 'Response Code')
        
        return sampler_tree
    
    def add_response_assertion(self, parent: ET.Element, expected_value: str, field: str = 'Response Code'):
        """Add a response assertion"""
        assertion = ET.SubElement(parent, 'ResponseAssertion', {
            'guiclass': 'AssertionGui',
            'testclass': 'ResponseAssertion',
            'testname': f'Assert {field}',
            'enabled': 'true'
        })
        
        test_strings = ET.SubElement(assertion, 'collectionProp', {'name': 'Asserion.test_strings'})
        ET.SubElement(test_strings, 'stringProp', {'name': '49586'}).text = expected_value
        
        ET.SubElement(assertion, 'stringProp', {'name': 'Assertion.custom_message'})
        
        if field == 'Response Code':
            ET.SubElement(assertion, 'stringProp', {'name': 'Assertion.test_field'}).text = 'Assertion.response_code'
        else:
            ET.SubElement(assertion, 'stringProp', {'name': 'Assertion.test_field'}).text = 'Assertion.response_data'
        
        ET.SubElement(assertion, 'boolProp', {'name': 'Assertion.assume_success'}).text = 'false'
        ET.SubElement(assertion, 'intProp', {'name': 'Assertion.test_type'}).text = '8'  # Equals
        
        ET.SubElement(parent, 'hashTree')
    
    def add_simple_controller(self, parent: ET.Element, name: str) -> ET.Element:
        """Add a Simple Controller for organizing requests (folders)"""
        controller = ET.SubElement(parent, 'GenericController', {
            'guiclass': 'LogicControllerGui',
            'testclass': 'GenericController',
            'testname': name,
            'enabled': 'true'
        })
        
        controller_tree = ET.SubElement(parent, 'hashTree')
        return controller_tree
    
    def process_items(self, items: List[Dict], parent: ET.Element):
        """Process Postman collection items recursively"""
        for item in items:
            if 'item' in item:
                # It's a folder
                folder_name = item.get('name', 'Folder')
                folder_tree = self.add_simple_controller(parent, folder_name)
                self.process_items(item['item'], folder_tree)
            else:
                # It's a request
                request_name = item.get('name', 'HTTP Request')
                self.add_http_sampler(parent, item, request_name)
    
    def convert(self, postman_file: str, output_file: str, env_file: Optional[str] = None):
        """Convert Postman collection to JMeter JMX"""
        # Load Postman collection
        try:
            with open(postman_file, 'r', encoding='utf-8') as f:
                collection = json.load(f)
        except Exception as e:
            print(f"Error loading Postman collection: {e}")
            return False
        
        # Load environment if provided
        if env_file:
            self.load_environment(env_file)
        
        # Get collection info
        info = collection.get('info', {})
        collection_name = info.get('name', 'Test Plan')
        
        # Create JMX structure
        self.create_jmx_structure(collection_name)
        
        # Add thread group
        thread_group_tree = self.add_thread_group(f"{collection_name} - Thread Group")
        
        # Process all items
        items = collection.get('item', [])
        self.process_items(items, thread_group_tree)
        
        # Write to file
        try:
            xml_str = minidom.parseString(ET.tostring(self.jmx_root, encoding='unicode')).toprettyxml(indent='  ')
            # Remove empty lines
            xml_str = '\n'.join([line for line in xml_str.split('\n') if line.strip()])
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(xml_str)
            
            print(f"✓ Successfully converted '{postman_file}' to '{output_file}'")
            return True
        except Exception as e:
            print(f"Error writing JMX file: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert Postman Collection JSON to JMeter JMX format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python convert_postman_to_jmx.py collection.json
  python convert_postman_to_jmx.py collection.json -o output.jmx
  python convert_postman_to_jmx.py collection.json -e environment.json -o test.jmx
        '''
    )
    
    parser.add_argument('input', help='Input Postman collection JSON file')
    parser.add_argument('-o', '--output', help='Output JMeter JMX file (default: input name with .jmx extension)')
    parser.add_argument('-e', '--environment', help='Postman environment JSON file (optional)')
    
    args = parser.parse_args()
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(args.input)[0]
        output_file = f"{base_name}.jmx"
    
    # Convert
    converter = PostmanToJMeterConverter()
    success = converter.convert(args.input, output_file, args.environment)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()