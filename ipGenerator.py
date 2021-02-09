import ipaddress
import pprint
import yaml
import re

topology_file = 'Topo.txt'
ip = "192.168.1.0"
mask = "255.255.255.0"
# loopback ip subnet, again assuming a /24
loop_ip = "192.168.2.0"
linkmask = '/31'


def read_file(file):
    with open(file, 'r') as f:
        topo = yaml.load(f, Loader=yaml.FullLoader)
    return topo

def get_srl_nodes(topo):
    """ Create a list of nodes for SRL alone"""
    srl_nodes = []
    for node, value in topo['topology']['nodes'].items():
        if value['kind'] == 'srl':
            srl_nodes.append(node)
    return srl_nodes

def get_srl_links(topo, nodes):
    """ Gets a list of links for SRL nodes alone. Also convert the interface naming from say e1-1 to ethernet-1/1"""
    links = []
    for link in topo['topology']['links']:
        node1 = re.findall(r'(.+):(.+$)', link['endpoints'][0])[0][0]
        node2 = re.findall(r'(.+):(.+$)', link['endpoints'][1])[0][0]
        if all(x in nodes for x in [node1, node2]):
            links.append([re.findall(r'(.+):(.+$)', link['endpoints'][0])[0][0],
                  re.findall(r'(.+):(.+$)', link['endpoints'][0])[0][1].replace('-', '/').replace('e', 'ethernet-'),
                  re.findall(r'(.+):(.+$)', link['endpoints'][1])[0][0],
                  re.findall(r'(.+):(.+$)', link['endpoints'][1])[0][1].replace('-', '/').replace('e', 'ethernet-')]
                  )
    return links






List_of_networks = list(ipaddress.ip_network(ip+'/'+mask).subnets(new_prefix=31))
list_of_loopback = list(ipaddress.ip_network(loop_ip+'/'+mask))


def generate_ip_subnet(y):
    for i in y:
        yield i

def generate_ip_address(y):
    for i in y:
        yield i

def wildcard_conversion(mask):
    wildcard = []
    for x in mask.split('.'):
        component = 255 - int(x)
        wildcard.append(str(component))
    wildcard = '.'.join(wildcard)
    return wildcard


topo = read_file(topology_file)
nodes = get_srl_nodes(topo)



master_dict = dict()
g = generate_ip_subnet(List_of_networks)
lo = generate_ip_address(list_of_loopback)
for i in get_srl_links(topo, nodes):
    n = ipaddress.ip_network(next(g))
    first_ip = next(n.hosts())
    second_ip = ipaddress.ip_address(first_ip + 1)
    if i[0] in master_dict:
        master_dict[i[0]]["interface"].append([i[1], str(first_ip) + linkmask, "Connects to " + i[2] + " at " + i[3]])
    else:
        master_dict[i[0]] = {
            "interface": [[i[1], str(first_ip) + linkmask, "Connects to " + i[2] + " at " + i[3]]],
            "root_ip": str(next(lo)),
            "area": 0,
            "mpls": True
            }
    if i[2] in master_dict:
        master_dict[i[2]]["interface"].append([i[3], str(second_ip) + linkmask, "Connects to " + i[0] + " at " + i[1]])
    else:
        master_dict[i[2]] = {
            "interface": [[i[3], str(second_ip) + linkmask, "Connects to " + i[0] + " at " + i[1]]],
            "root_ip": str(next(lo)),
            "area": 0,
            "mpls": True
            }
pprint.pprint(master_dict)