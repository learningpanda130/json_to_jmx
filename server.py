import asyncio
import json
import tempfile
import os
import subprocess
from mcp.server.fastmcp import FastMCP
from mcp import types
from mcp.types import TextContent, CallToolResult
from convert_postman_to_jmx import PostmanToJMeterConverter

server = FastMCP('postman2jmx-server')

@server.tool(name='postman_to_jmx', description='Convert postman collection json into Jmeter jmx xml')
def postman_to_jmx(args: dict):
    try:
        collection_json = args.get('collection')
        environment_json = args.get('environment')
        output_path = args.get('output', 'output.jmx')

        if not collection_json:
            return CallToolResult(content=[TextContent(type="text", text="Error: missing collection argument")])

        # Write collection to temp file
        temp_collection = None
        temp_env = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(collection_json)
                temp_collection = f.name

            if environment_json:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    f.write(environment_json)
                    temp_env = f.name

            converter = PostmanToJMeterConverter()
            success = converter.convert(temp_collection, output_path, temp_env)

            if success:
                with open(output_path, 'r', encoding='utf-8') as f:
                    jmx_text = f.read()
                return CallToolResult(content=[TextContent(type="text", text=jmx_text)])
            else:
                return CallToolResult(content=[TextContent(type="text", text="Error: Conversion failed")])
        finally:
            # Clean up temp files
            if temp_collection and os.path.exists(temp_collection):
                os.unlink(temp_collection)
            if temp_env and os.path.exists(temp_env):
                os.unlink(temp_env)
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")])

@server.tool(name='run_jmeter', description='Run JMeter performance test on a JMX file')
def run_jmeter(args: dict):
    try:
        jmx_path = args.get('jmx_path')
        results_path = args.get('results_path', 'jmeter_results.csv')

        if not jmx_path:
            return CallToolResult(content=[TextContent(type="text", text="Error: missing jmx_path argument")])

        # Run JMeter via Docker
        result = subprocess.run([
            'docker', 'run', '--rm',
            '-v', f'{os.getcwd()}:/jmeter',
            '-w', '/jmeter',
            'justb4/jmeter:latest',
            '-n', '-t', jmx_path, '-l', results_path
        ], capture_output=True, text=True)

        output = f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}\nReturn Code: {result.returncode}\n"

        if result.returncode == 0:
            # Read results
            if os.path.exists(results_path):
                with open(results_path, 'r') as f:
                    results = f.read()
                return CallToolResult(content=[TextContent(type="text", text=output + f"JMeter run successful. Results:\n{results}")])
            else:
                return CallToolResult(content=[TextContent(type="text", text=output + "JMeter run successful, but results file not found.")])
        else:
            return CallToolResult(content=[TextContent(type="text", text=output + f"JMeter error: {result.stderr}")])
    except Exception as e:
        return CallToolResult(content=[TextContent(type="text", text=f"Error: {str(e)}")])

async def main():
    pass

if __name__ == "__main__":
    server.run()
