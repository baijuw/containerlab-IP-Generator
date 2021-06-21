import ipaddress
import yaml
import re
import pickle
import pprint
import jinja2
import os

topology_file = 'Topo.txt'
ip = "192.168.1.0"
mask = "255.255.255.0"
# loopback ip subnet, again assuming a /24
rid_ip = "10.0.0.0"
linkmask = '/31'
network_instance= "default"
leaf_file = "leaf.jinja2"
spine_file = "spine.jinja2"


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
    #pprint.pprint(links)
    return links


List_of_networks = list(ipaddress.ip_network(ip+'/'+mask).subnets(new_prefix=31))
list_of_loopback = list(ipaddress.ip_network(rid_ip + '/' + mask))


def generate_ip_subnet(y):
    for _i in y:
        yield _i


def generate_ip_address(y):
    for _i in y:
        yield _i


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
rid = generate_ip_address(list_of_loopback)

first_as, second_as = 0, 0
for i in get_srl_links(topo, nodes):
    n = ipaddress.ip_network(next(g))
    first_ip = next(n.hosts())
    second_ip = ipaddress.ip_address(first_ip + 1)
    first_as = topo["topology"]["nodes"][i[0]]["env"]["bgpas"]
    second_as = topo["topology"]["nodes"][i[2]]["env"]["bgpas"]
    if i[0] in master_dict:
        master_dict[i[0]]["interfaces"].append({"name": i[1], "ip": str(first_ip) + linkmask, "comments": "Connects to " + i[2] + " at " + i[3]})
        if {"name": "AS-" + str(second_as), "peer_as": second_as} not in master_dict[i[0]]["bgp"]["group"]:
            master_dict[i[0]]["bgp"]["group"].append({"name": "AS-" + str(second_as), "peer_as": second_as})
        if {"ip": str(second_ip), "peer_group": "AS-" + str(second_as)} not in master_dict[i[0]]["bgp"]["neighbor"]:
            master_dict[i[0]]["bgp"]["neighbor"].append({"ip": str(second_ip), "peer_as": str(second_as)})
    else:
        master_dict[i[0]] = {
            "interfaces": [{"name": i[1],
                           "ip": str(first_ip) + linkmask,
                           "comments": "Connects to " + i[2] + " at " + i[3]}],
            "ospf": {"area": 0},
            "network_instance": network_instance,
            "bgp": {"as": first_as,
                    "rid": topo["topology"]["nodes"][i[0]]["env"]["rid"],
                    "group": [{"name": "AS-" + str(second_as), "peer_as": second_as}],
                    "neighbor": [{"ip": str(second_ip), "peer_as":  str(second_as)}]
                    },
            "level": topo["topology"]["nodes"][i[0]]["env"]["level"]
            }
    if i[2] in master_dict:
        master_dict[i[2]]["interfaces"].append({"name": i[3], "ip": str(second_ip) + linkmask, "comments":"Connects to " + i[0] + " at " + i[1]})
        if {"name": "AS-" + str(first_as), "peer_as": first_as} not in master_dict[i[2]]["bgp"]["group"]:
            master_dict[i[2]]["bgp"]["group"].append({"name": "AS-" + str(first_as), "peer_as": first_as})
        if {"ip": str(first_ip), "peer_group": "AS-" + str(first_as)} not in master_dict[i[2]]["bgp"]["neighbor"]:
            master_dict[i[2]]["bgp"]["neighbor"].append({"ip": str(first_ip), "peer_as": str(first_as)})
    else:
        master_dict[i[2]] = {
            "interfaces": [{"name": i[3],
                           "ip": str(second_ip) + linkmask,
                           "comments":"Connects to " + i[0] + " at " + i[1]}],
            "ospf": {"area": 0},
            "network_instance": network_instance,
            "bgp": {"as": second_as,
                    "rid": topo["topology"]["nodes"][i[2]]["env"]["rid"],
                    "group": [{"name": "AS-" + str(first_as), "peer_as": first_as}],
                    "neighbor": [{"ip": str(first_ip), "peer_as": str(first_as)}]
                    },
            "level": topo["topology"]["nodes"][i[2]]["env"]["level"]
            }
#pprint.pprint(master_dict)

with open('master_dict.pickle', 'wb+') as f:
    pickle.dump(master_dict, f, protocol=pickle.HIGHEST_PROTOCOL)


templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader)
leaf_template = templateEnv.get_template(leaf_file)
spine_template = templateEnv.get_template(spine_file)


if not os.path.exists('fullconfig/'):
    os.makedirs('fullconfig')
for key, value in master_dict.items():
    pprint.pprint(value)
    if value["level"] == 'leaf':
        outputText = leaf_template.render(srl_input=value)
        with open('fullconfig/'+key, "w+") as f:
            f.write(outputText)
    elif value["level"] == 'spine':
        outputText = spine_template.render(srl_input=value)
        with open('fullconfig/' + key, "w+") as f:
            f.write(outputText)
