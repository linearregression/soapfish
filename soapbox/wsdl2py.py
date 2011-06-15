import sys
from optparse import OptionParser
from lxml import etree
from jinja2 import Template,Environment
from wsdl import Definitions
from utils import removens, classyfiy, get_get_type, use, find_xsd_namepsace,urlcontext
from xsd2py import TEMPLATE as SCHEMA_TEMPLATE

environment = Environment()
environment.filters["class"] = classyfiy
environment.filters["removens"] = removens
environment.filters["use"] = use
environment.filters["urlcontext"] = urlcontext

TEMPLATE = """#This was was generated by wsdl2py, try to not edit.
from soapbox import soap
{%- if schema %}
{{schema}}
{%- else %}
from soapbox import xsd
{%- endif %}

{%- for service in definitions.services %}

{%- set binding = definitions.get_by_name(definitions.bindings, service.port.binding) %}
{%- set portType = definitions.get_by_name(definitions.portTypes, binding.type) %}
{%- set inputMessage = definitions.get_by_name(definitions.messages, portType.operation.input.message) %}
{%- set outputMessage = definitions.get_by_name(definitions.messages, portType.operation.output.message) %}

{% if is_server %}
def {{binding.operation.name}}({{inputMessage.part.element|removens}}):
    #Put your implementation here.
    return {{outputMessage.part.element|removens}}
{%- endif %}
    
{{binding.operation.name}}_method = xsd.Method(
    {%- if is_server %}function = {{binding.operation.name}},{% endif %}
    soapAction = "{{binding.operation.operation.soapAction}}",
    {%- if inputMessage.part.element %}  
    input = "{{inputMessage.part.element|removens}}",#Pointer to Schema.elements
    {%- else %}
    input = {{inputMessage.part.type|removens|class}},
    {%- endif %}
    {%- if inputMessage.part.element %}  
    output = "{{outputMessage.part.element|removens}}",#Pointer to Schema.elements
    {%- else %}
    input = {{outputMessage.part.type|removens|class}},
    {%- endif %}
    operationName = "{{binding.operation.name}}")
    
SERVICE = soap.Service(
    targetNamespace = "{{definitions.targetNamespace}}",
    location = "{{service.port.address.location}}",
    schema = Schema,
    methods = [{{binding.operation.name}}_method, ])
    
{% if is_server %}
#Uncomment this lines to turn on dispatching. 
#from django.views.decorators.csrf import csrf_exempt
#dispatch = csrf_exempt(soap.get_django_dispatch(SERVICE))

#Put this lines in your urls.py:
#urlpatterns += patterns('',
#    (r"{{service.port.address.location|urlcontext}}", "<fill the module path>.dispatch")
#)
{%- else %}
class ServiceStub(soap.Stub):
    SERVICE = SERVICE
    
    def {{binding.operation.name}}(self, {{inputMessage.part.element|removens}}):
        return self.call("{{binding.operation.name}}", {{inputMessage.part.element|removens}})
{%- endif %} 
{% endfor %}
"""

def generate_code_from_wsdl(is_server, xml):
    xmlelement = etree.fromstring(xml)
    XSD_NAMESPACE = find_xsd_namepsace(xmlelement.nsmap)
    environment.filters["type"] = get_get_type(XSD_NAMESPACE)
    definitions = Definitions.parse_xmlelement(xmlelement)
    schema = definitions.types.schema
    schemaxml = environment.from_string(SCHEMA_TEMPLATE).render(schema=schema)
    return environment.from_string(TEMPLATE).render(
            definitions=definitions,
            schema=schemaxml,
            is_server=is_server)
    
def console_main():
    parser = OptionParser(usage = "usage: %prog [-c|-s] path_to_wsdl")
    parser.add_option("-c", "--client", dest="client",
                  help="Generate webservice http client code.")
    parser.add_option("-s", "--server", dest="server",
                  help="Generate webservice Django server code.")
    (options, args) = parser.parse_args()
    if options.client and options.server:
        parser.error("Options -c and -s are mutually exclusive")
    elif options.client:
        xml = open(options.client).read()
        print generate_code_from_wsdl(False, xml)
    elif options.server:
        xml = open(options.server).read()
        print generate_code_from_wsdl(True, xml)
    else:
        parser.print_help()
        
if __name__ == "__main__":
    console_main()