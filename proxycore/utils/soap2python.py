import copy
import re
import sys
import xml.etree.ElementTree as etree

method_name_re = re.compile(r'^[a-zA-Z0-9_]+$')
number_re = re.compile(r'^[0-9]+(\.[0-9]+)?$')


def reconstruct_tree_from_hrefs(root, hrefs):
    for child in root:
        if 'href' in child.attrib:
            refid = child.attrib['href']
            if len(refid) > 1 and refid[0] == '#':
                id = refid[1:]
                if id in hrefs:
                    subchild = hrefs[id]
                    if '{http://www.w3.org/2001/XMLSchema-instance}type' in subchild.attrib:
                        child.attrib['{http://www.w3.org/2001/XMLSchema-instance}type'] = subchild.attrib['{http://www.w3.org/2001/XMLSchema-instance}type']
                    elif '{http://schemas.xmlsoap.org/soap/encoding/}arrayType' in subchild.attrib:
                        child.attrib['{http://schemas.xmlsoap.org/soap/encoding/}arrayType'] = subchild.attrib['{http://schemas.xmlsoap.org/soap/encoding/}arrayType']
                    for sschild in subchild:
                        child.append(copy.deepcopy(sschild))
                    del child.attrib['href']
        reconstruct_tree_from_hrefs(child, hrefs)
    return root


def make_hrefs_table(root):
    hrefs = {}
    for child in root:
        if 'id' in child.attrib:
            hrefs[child.attrib['id']] = child
        hrefs.update(make_hrefs_table(child))
    return hrefs


def parse_soap_from_file(filename):
    try:
        return parse_soap(etree.parse(filename).getroot())
    except Exception as e:
        print("Cannot parse filename " + filename, file=sys.stderr)
        print(e)


def parse_soap_from_string(string):
    return parse_soap(etree.fromstring(string))


def parse_soap(root):
    body = None
    for element in root:
        if element.tag.endswith('Body'):
            body = element
    if body is None:
        return None

    hrefs = make_hrefs_table(body)
    if len(hrefs) > 0:
        return reconstruct_tree_from_hrefs(body, hrefs)[0]
    else:
        return body[0]


def normalize_tag(name):
    if name[0] == "{":
        uri, tag = name[1:].split("}")
        return tag
    else:
        return name


def translate_value(val, level):
    if number_re.match(val):
        return val
    elif val == "true":
        return "True"
    elif val == "false":
        return "False"
    else:
        return "r\"%s\"" % val.replace("\n", "\\n\"\n" + ("    " * (level+2)) + " + r\"")


def print_identifier(name, api_name):
    if not name:
        return "%s" % api_name
    elif not method_name_re.match(name):
        return "%s[\"%s\"]" % (api_name, name)
    else:
        return "%s.%s" % (api_name, name)


def determine_tag_name(element):
    if "{http://www.w3.org/2001/XMLSchema-instance}type" in element.attrib:
        return element.attrib["{http://www.w3.org/2001/XMLSchema-instance}type"].split(":")[1]
    else:
        return None


def is_array(element, tag_name):
    return tag_name == "Array" or '{http://schemas.xmlsoap.org/soap/encoding/}arrayType' in element.attrib
    # TODO: For API2 we will need to actually investigate the contents of the element - is it not named Array


def print_element(element, api_name, level):
    tag_name = determine_tag_name(element)
    output = ""
    if is_array(element, tag_name):
        output += "[\n"
        output += print_array(element, api_name, level+1)
        output += "    " * level + "]"
    else:
        output += print_identifier(tag_name, api_name)
        output += "(\n"
        output += print_args(element, api_name, level+1)
        output += "    " * level + ")"
    return output


def merge_repeated_children(element):
    children = []
    children_by_tag = {}
    max_len = 0

    for child in element:
        by_tag = children_by_tag.get(child.tag, [])
        by_tag.append(child)
        children_by_tag[child.tag] = by_tag

        max_len = max(len(by_tag), max_len)
        children.append(child)

    if max_len > 1:
        children = []
        for child in element:
            if child.tag in children_by_tag:
                all_children = children_by_tag[child.tag]
                if len(all_children) > 1:
                    list_elem = etree.Element(child.tag)
                    list_elem.attrib['{http://schemas.xmlsoap.org/soap/encoding/}arrayType'] = child.tag
                    for c in all_children:
                        list_elem.append(c)
                    children.append(list_elem)
                else:
                    children.append(child)
                del children_by_tag[child.tag]

    return children


def print_array(element, api_name, level):
    first = True
    output = ""
    for child in element:
        if not first:
            output += ",\n"
        else:
            first = False
        output += "    " * level
        if len(child):
            output += print_element(child, api_name, level)
        elif child.text:
            output += translate_value(child.text, level)
        else:
            output += "None"

    output += "\n"
    return output


def print_args(element, api_name, level=1):
    first = True
    output = ""
    for child in merge_repeated_children(element):
        if not first:
            output += ",\n"
        else:
            first = False
        output += "    " * level
        output += normalize_tag(child.tag) + "="
        if len(child):
            output += print_element(child, api_name, level)
        elif child.text:
            output += translate_value(child.text, level)
            output += ""
        else:
            output += "None"

    output += "\n"
    return output


def print_method(element, api_name, level=0):
    method_name = normalize_tag(element.tag)
    output = print_identifier(method_name, api_name)
    output += "(\n"
    output += print_args(element, api_name, level=level + 1)
    output += "    " * level + ")\n"
    return output


def get_client_from_path(path):
    return "UNKNOWN_CLIENT"

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print("Usage: %s API_NAME XML_FILE (XML_FILE2 ...)" % sys.argv[0])
        print("Scripts reads recorded soap request and translates it to Python code to be used in tests")
        print("   XML_FILE = input file")
        print("   API_NAME = name of the client to be generated, such as 'client_ui' or 'self.client.ui2'")
        exit(1)

    client_name = sys.argv[1]
    files = sys.argv[2:]

    for f in files:
        method_element = parse_soap_from_file(f)
        if method_element is None:
            print("Unable to find method call element in file %s" % f, file=sys.stderr)
        else:
            print("# file: %s" % f)
            print(print_method(method_element, client_name))
