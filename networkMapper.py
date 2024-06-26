import pprint
import shlex
import sys
import pathlib
import json
import secrets

from graphviz import Digraph

def get(source, index):
	try:
		return source[index]
	except IndexError:
		return ''
	except KeyError:
		return ''

# TODO: Allow defining a new type, that has a scheme of attributes attached. (X is a new Type, X has a Shape of box3d, etc.)

def parse_line(index, line):
	r = {}
	r['kind'] = 'metadata'
	r['content'] = {}

	tokens = shlex.split(line, comments=False, posix=True)
	unknown_count = 0

	if get(tokens, 1).lower() == 'has' and (get(tokens, 2).lower() == 'a' or get(tokens, 2).lower() == 'an') and get(tokens, 4).lower() == 'of':
		# x has a THING of VALUE
		r['kind'] = 'metadata'
		name = get(tokens, 0)
		attribute = get(tokens, 3)
		value = get(tokens, 5)

		r['content']['Name A'] = name
		r['content']['Metadata'] = {}
		r['content']['Metadata'][attribute] = value
	elif get(tokens, 1).lower() == 'is' and get(tokens, 2).lower() == 'a':
		r['kind'] = 'metadata'
		name = get(tokens, 0)
		attribute = 'Type'
		value = get(tokens, 3)

		r['content']['Name A'] = name
		r['content']['Metadata'] = {}
		r['content']['Metadata'][attribute] = value
	elif get(tokens, 1).lower() == 'is' and get(tokens, 2).lower() == 'connected' and get(tokens, 3).lower() == 'to' and get(tokens, 5).lower() == 'via':
		# x is connected to y via wifi
		r['kind'] = 'statement'
		name_a = get(tokens, 0)
		name_b = get(tokens, 4)
		relation = get(tokens, 6)

		r['content']['Name A'] = name_a
		r['content']['Name B'] = name_b
		r['content']['Relation'] = relation

	elif get(tokens, 1).lower() == 'is' and get(tokens, 2).lower() == 'connected' and get(tokens, 3).lower() == 'to':
		# x is connected to y
		r['kind'] = 'statement'
		name_a = get(tokens, 0)
		name_b = get(tokens, 4)

		r['content']['Name A'] = name_a
		r['content']['Name B'] = name_b
		r['content']['Relation'] = 'ethernet'
	elif get(tokens, 1).lower() == 'connects' and get(tokens, 2).lower() == 'to' and get(tokens, 4).lower() == 'via':
		# x connects to y via wifi
		r['kind'] = 'statement'
		name_a = get(tokens, 0)
		name_b = get(tokens, 3)
		relation = get(tokens, 5)

		r['content']['Name A'] = name_a
		r['content']['Name B'] = name_b
		r['content']['Relation'] = relation
	elif get(tokens, 1).lower() == 'connects' and get(tokens, 2).lower() == 'to':
		# x connects to y
		r['kind'] = 'statement'
		name_a = get(tokens, 0)
		name_b = get(tokens, 3)

		r['content']['Name A'] = name_a
		r['content']['Name B'] = name_b
		r['content']['Relation'] = 'ethernet'
	else:
		print("WARNING: Line skipped.", line, file=sys.stderr)

	return r

def parse_file(filename, require_legend=True):
	r = {
		'metadata': [],
		'statement': []
	}

	with open(filename, 'r') as openFile:
		index = 0
		for line in openFile:
			if line and line.rstrip() and line.rstrip()[0] != '#':
				x = parse_line(index, line.strip())
				if x['kind'] == 'metadata':
					r['metadata'].append(x['content'])
				else:
					r['statement'].append(x['content'])
			index = index + 1
		if require_legend:
			for line in legend():
				if line and line.rstrip() and line.rstrip()[0] != '#':
					x = parse_line(index, line.strip())
					if x['kind'] == 'metadata':
						r['metadata'].append(x['content'])
					else:
						r['statement'].append(x['content'])
				index = index + 1

	r2 = []
	for statement in r['statement']:
		r2.append(statement)
	for metastatement in r['metadata']:
		r2.append(metastatement)

	return r2

def assemble_dtree(names, idents, tree):
	data = {}
	for name in names:
		data[name] = {"index": idents[name]}

	for row in tree:
		if not row:
			continue

		name = row['Name A']

		try:
			for k, v in row['Metadata'].items():
				try:
					data[name]['meta']
				except KeyError:
					data[name]['meta'] = {}

				try:
					if not isinstance(data[name]['meta'][k], list):
						data[name]['meta'][k] = [data[name]['meta'][k]]
					data[name]['meta'][k].append(v)
				except KeyError:
					data[name]['meta'][k] = v
		except KeyError:
			pass

		try:
			data[name]['relations']
		except KeyError:
			data[name]['relations'] = []

		try:
			data[name]['relations'].append({
				'kind': row['Relation'],
				"to": row['Name B']
			})
		except KeyError:
			pass

		try:
			name_b = row['Name B']

			try:
				data[name_b]['meta']
			except KeyError:
				data[name_b]['meta'] = {}

			try:
				data[name_b]['relations']
			except KeyError:
				data[name_b]['relations'] = []
		except KeyError:
			pass

	return data

def retree(names, data):
	proper_tree = []
	for name in names:
		subdata = data[name].copy()

		try:
			subdata['relations']
		except KeyError:
			unknown_found = True
			subdata['relations'] = [{'to': name, "kind":"unknown"}]

		for relation in subdata['relations']:
			row = {}
			row['Name A'] = name
			row['Name B'] = relation['to']
			row['Relation'] = relation['kind']
			proper_tree.append(row)

	for name in names:
		found = False
		for row in proper_tree:
			if row['Name A'] == name or row['Name B'] == name:
				found = True
				break
		if not found:
			row = {}
			row['Name A'] = name
			row['Name B'] = name
			row['Relation'] = 'unknown'
			proper_tree.append(row)

	return proper_tree

def legend():
	return """Legend:{prefix}LegendLoc has a Type of Location
Legend:{prefix}LegendLoc has a Blurb of "All items may have a Blurb, such as this. They may also have any arbitrary attribute, such as an IPAddress, OS, or any named key."

Ethernet:{prefix}LegendVMEth has a Type of Note
Ethernet:{prefix}LegendVMEth is connected to Legend:{prefix}LegendLoc via Ethernet
Ethernet:{prefix}LegendVMEth has a Blurb of "Blue lines indicate an Ethernet Connection."

WiFi:{prefix}LegendVMWifi has a Type of Note
WiFi:{prefix}LegendVMWifi is connected to Legend:{prefix}LegendLoc via WiFi
WiFi:{prefix}LegendVMWifi has a Blurb of "Green lines indicate a WiFi Connection."

Physical:{prefix}LegendVMPhys has a Type of Note
Physical:{prefix}LegendVMPhys is connected to Legend:{prefix}LegendLoc via Physical
Physical:{prefix}LegendVMPhys has a Blurb of "Black lines indicate a Physical Connection."

Unknown:{prefix}LegendVMUknown has a Type of Note
Unknown:{prefix}LegendVMUknown is connected to Legend:{prefix}LegendLoc via unknown
Unknown:{prefix}LegendVMUknown has a Blurb of "Grey lines specify an unknown connection type."

Router:{prefix}LegendRouter has a Type of Router
Router:{prefix}LegendRouter has a IPAddress of 192.168.0.1
Router:{prefix}LegendRouter is connected to Legend:{prefix}LegendLoc via Physical

Switch:{prefix}LegendSwitch has a Type of Switch
Switch:{prefix}LegendSwitch is connected to Legend:{prefix}LegendLoc via Ethernet

Phone:{prefix}LegendPhone has a Type of Phone
Phone:{prefix}LegendPhone is connected to Legend:{prefix}LegendLoc via WiFi

PC:{prefix}LegendPC has a Type of PC
PC:{prefix}LegendPC is connected to Legend:{prefix}LegendLoc via Ethernet

Laptop:{prefix}LegendLaptop has a Type of Laptop
Laptop:{prefix}LegendLaptop is connected to Legend:{prefix}LegendLoc via WiFi
Laptop:{prefix}LegendLaptop is connected to Legend:{prefix}LegendLoc via Ethernet

VM:{prefix}LegendVM has a Type of VirtualMachine
VM:{prefix}LegendVM is connected to Legend:{prefix}LegendLoc

Unknown:{prefix}LegendUnknown has a Blurb of "no type given"
Unknown:{prefix}Legend is connected to Legend:{prefix}LegendLoc

Shape:{prefix}Legend2 has a Type of Note
Shape:{prefix}Legend2 has a Shape of "triangle"
Shape:{prefix}Legend2 has a Blurb of "Custom shapes are provided by the Shape attribute.\\nAnything that DOT/graphviz would understand is accepted."
Shape:{prefix}Legend2 is connected to Legend:{prefix}LegendLoc via Physical
	""".format(prefix=secrets.token_hex(16)).split("\n")

def main(tree, output_filename, require_legend=True):
	dot = Digraph(graph_attr = {
		'splines':'ortho',
		'strict': 'false',
		'overlap': 'false'
	},
	engine='neato')

	names = []
	for i in tree:
		try:
			names.append(i['Name A'])
		except KeyError:
			pass
		try:
			names.append(i['Name B'])
		except KeyError:
			pass
	names = list(set(names))

	idents = {}
	for index, name in enumerate(names):
		idents[name] = str(index)

	data = assemble_dtree(names, idents, tree)
	proper_tree = retree(names, data)

	symbol_shapes = {
		"server": "cylinder",
		"router": "diamond",
		"switch": "invtriangle",
		"laptop": "box3d",
		"pc": "box3d",
		"phone": "box3d",
		"virtualmachine": "circle",
		"location": "Msquare",
		"unknown": "doublecircle",
		"component": "component",
		"note": "note",
		"group": "folder",
		"subgroup": "tab",
		"e-signature": "signature",
		"site": "Msquare"
	}
	# TODO: Allow colour, other properties, overriding...?

	edges = {}
	for row in proper_tree:
		with dot.subgraph() as sub:
			try:
				shape_a = symbol_shapes[data[row['Name A']]['meta']['Type'].lower().replace("virtual_machine", "virtualmachine").replace("virtual machine", "virtualmachine")]
			except KeyError:
				shape_a = symbol_shapes['unknown']
			except AttributeError:
				shape_a = symbol_shapes[data[row['Name A']]['meta']['Type'][0].lower()]

			try:
				shape_a = get(data[row['Name A']]['meta'], 'Shape') or shape_a
			except KeyError:
				pass

			try:
				meta_details = data[row['Name A']]['meta'].copy()
				try:
					meta_details['Blurb']
					del meta_details['Blurb']
				except KeyError:
					pass

				try:
					meta_details['Shape']
					del meta_details['Shape']
				except KeyError:
					pass

				try:
					meta_details['DisplayName']
					del meta_details['DisplayName']
				except KeyError:
					pass

				details_a = json.dumps(meta_details, indent=4, sort_keys=True)[1:-1]
			except KeyError:
				details_a = ''

			try:
				shape_b = symbol_shapes[data[row['Name B']]['meta']['Type'].lower()]
			except KeyError:
				shape_b = symbol_shapes['unknown']
			except AttributeError:
				shape_b = symbol_shapes[data[row['Name B']]['meta']['Type'][0].lower()]

			try:
				shape_a = get(data[row['Name B']]['meta'], 'Shape') or shape_a
			except KeyError:
				pass

			try:
				meta_details = data[row['Name B']]['meta'].copy()
				try:
					meta_details['Blurb']
					del meta_details['Blurb']
				except KeyError:
					pass

				try:
					meta_details['Shape']
					del meta_details['Shape']
				except KeyError:
					pass

				try:
					meta_details['DisplayName']
					del meta_details['DisplayName']
				except KeyError:
					pass

				details_b = json.dumps(meta_details, indent=4, sort_keys=True)[1:-1]
			except KeyError:
				details_b = ''

			try:
				blurb_a = "\n" + '.\n'.join(data[row['Name A']]['meta']['Blurb'].split("."))
			except KeyError:
				blurb_a = ''

			try:
				blurb_b = "\n" + '.\n'.join(data[row['Name B']]['meta']['Blurb'].split("."))
			except KeyError:
				blurb_b = ''

			try:
				label_a = data[row['Name A']]['meta']['DisplayName']
			except:
				label_a = row['Name A'].split(":", 1)[0]

			try:
				label_b = data[row['Name B']]['meta']['DisplayName']
			except:
				label_b = row['Name B'].split(":", 1)[0]

			colour_scheme = {
				"telnet": "red",
				"ethernet": "blue",
				"wifi": "green",
				"physical": "black",
				"other": "grey",
				"unknown": "grey"
			}

			try:
				color_a = colour_scheme[data[row['Name A']]['relations'][0]['kind'].lower()]
			except (IndexError, KeyError):
				color_a = colour_scheme['other']

			label_a = label_a + blurb_a + "\n" + details_a
			try:
				if data[row['Name A']]['meta']['Type'].lower() == "e-signature":
					label_a = blurb_a
			except KeyError:
				pass
			except AttributeError:
				pass

			label_b = label_b + blurb_b + "\n" + details_b
			try:
				if get(data[row['Name B']]['meta'], 'Type').lower() == "e-signature":
					label_b = blurb_b
			except KeyError:
				pass
			except AttributeError:
				pass	

			sub.node(name=idents[row['Name A']])

			try:
				if get(data[row['Name A']]['meta'], 'Type').lower() == "e-signature":
					margin_a="0.8"
				else:
					raise KeyError
			except KeyError:
				margin_a="1.2"
			except AttributeError:
				margin_a="1.2"

			try:
				if get(data[row['Name B']]['meta'], 'Type').lower() == "e-signature":
					margin_b="0.8"
				else:
					raise KeyError
			except KeyError:
				margin_b="1.2"
			except AttributeError:
				margin_a="1.2"

			try:
				if get(data[row['Name A']]['meta'], 'Type').lower() == "unknown":
					raise KeyError
				else:
					raise IndexError
			except KeyError:
				colour_a = "red"
			except IndexError:
				colour_a = "black"
			except AttributeError:
				colour_a = "black"

			try:
				if get(data[row['Name B']]['meta'], 'Type') == "unknown":
					raise KeyError
				else:
					raise IndexError
			except KeyError:
				colour_b = "red"
			except IndexError:
				colour_b = "black"
			except AttributeError:
				colour_b = "black"

			sub.node(name=idents[row['Name A']])
			sub.node(idents[row['Name A']], label=label_a, tooltip = details_a, shape = shape_a, color=colour_a, margin=margin_a)

			sub.node(name=idents[row['Name B']])
			sub.node(idents[row['Name B']], label=label_b, tooltip = details_b, shape = shape_b, color=colour_b, margin=margin_b)

			for rel in data[row['Name A']]['relations']:
				o_a = idents[row['Name A']]
				o_b = idents[rel['to']]

				try:
					colour_v = colour_scheme[rel['kind'].lower()]
				except (IndexError, KeyError):
					colour_v = colour_scheme['other']

				if o_a == o_b:
					try:
						edges[o_a + ":sw" + o_b.split(":", 1)[0] + rel['kind'].lower()]
					except KeyError:
						edges[o_a + ":sw" + o_b.split(":", 1)[0] + rel['kind'].lower()] = True
						sub.edge(o_a + ":sw", o_b.split(":", 1)[0], color=colour_v, dir='both', label=rel['kind'].lower())
				else:
					try:
						edges[o_a + o_b.split(":", 1)[0] + rel['kind'].lower()]
					except KeyError:
						edges[o_a + o_b.split(":", 1)[0] + rel['kind'].lower()] = True
						sub.edge(o_a, o_b.split(":", 1)[0], color=colour_v, dir='both', label=rel['kind'].lower())

	p = pathlib.Path(output_filename)
	dot.format = p.suffix[1:]
	return dot.render(p.stem)

# TODO: Ranges to generate multiples according to a template.

def cli():
	import argparse
	parser = argparse.ArgumentParser(description='Render a network tree.')
	parser.add_argument('-i', '--input-file', help='The input file to parse.', required=True)
	parser.add_argument('-o', '--output-file', help='The output file to render.', required=True)
	parser.add_argument('-l', '--legend', help='Add the legend to the output', action='store_true')
	parser.add_argument('-nl', '--no-legend', dest='legend', action='store_false')
	parser.set_defaults(legend=False)

	args = parser.parse_args()

	tree = parse_file(args.input_file, args.legend)
	main(tree, args.output_file, args.legend)

if __name__ == "__main__":
	cli()
