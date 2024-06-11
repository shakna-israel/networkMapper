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
		return type(source)()

def parse_line(index, line):
	r = {}
	r['kind'] = 'metadata'
	r['content'] = {}

	tokens = shlex.split(line, comments=False, posix=True)
	unknown_count = 0

	if get(tokens, 1) == 'has' and (get(tokens, 2) == 'a' or get(tokens, 2) == 'an') and get(tokens, 4) == 'of':
		# x has a THING of VALUE
		r['kind'] = 'metadata'
		name = get(tokens, 0)
		attribute = get(tokens, 3)
		value = get(tokens, 5)

		r['content']['Name A'] = name
		r['content']['Metadata'] = {}
		r['content']['Metadata'][attribute] = value
	elif get(tokens, 1) == 'is' and get(tokens, 2) == 'a':
		r['kind'] = 'metadata'
		name = get(tokens, 0)
		attribute = 'Type'
		value = get(tokens, 3)

		r['content']['Name A'] = name
		r['content']['Metadata'] = {}
		r['content']['Metadata'][attribute] = value
	elif get(tokens, 1) == 'is' and get(tokens, 2) == 'connected' and get(tokens, 3) == 'to' and get(tokens, 5) == 'via':
		# x is connected to y via wifi
		r['kind'] = 'statement'
		name_a = get(tokens, 0)
		name_b = get(tokens, 4)
		relation = get(tokens, 6)

		r['content']['Name A'] = name_a
		r['content']['Name B'] = name_b
		r['content']['Relation'] = relation

	elif get(tokens, 1) == 'is' and get(tokens, 2) == 'connected' and get(tokens, 3) == 'to':
		# x is connected to y
		r['kind'] = 'statement'
		name_a = get(tokens, 0)
		name_b = get(tokens, 4)

		r['content']['Name A'] = name_a
		r['content']['Name B'] = name_b
		r['content']['Relation'] = 'ethernet'
	else:
		print("WARNING: Line skipped.", line, file=sys.stderr)

	return r

def parse_file(filename):
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
		subdata = data[name]

		for relation in subdata['relations']:
			row = {}
			row['Name A'] = name
			row['Name B'] = relation['to']
			row['Relation'] = relation['kind']
			proper_tree.append(row)

	return proper_tree

def legend():
	return """Legend:{prefix}LegendLoc has a Type of Location
Legend:{prefix}LegendLoc has a Blurb of "Blue indicates an Ethernet Connection. Green indicates a WiFi Connection. Black, a Physical Connection. Grey, for any unspecified or unknown connections. All items may have a blurb, such as this. They may also have any arbitrary attribute, such as an IPAddress, OS, or any named key."

Router:{prefix}LegendRouter has a Type of Router
Router:{prefix}LegendRouter has a IPAddress of 192.168.0.1
Router:{prefix}LegendRouter is connected to Legend:{prefix}LegendLoc via Physical

Switch:{prefix}LegendSwitch has a Type of Switch
Switch:{prefix}LegendSwitch is connected to Router:{prefix}LegendRouter via Ethernet

Phone:{prefix}LegendPhone has a Type of Phone
Phone:{prefix}LegendPhone is connected to Switch:{prefix}LegendSwitch via WiFi

PC:{prefix}LegendPC has a Type of PC
PC:{prefix}LegendPC is connected to Switch:{prefix}LegendSwitch via Ethernet

Laptop:{prefix}LegendLaptop has a Type of Laptop
Laptop:{prefix}LegendLaptop is connected to Switch:{prefix}LegendSwitch via WiFi

VM:{prefix}LegendVM has a Type of VirtualMachine
VM:{prefix}LegendVM is connected to PC:{prefix}LegendPC

Unknown:{prefix}LegendUnknown has a Blurb of "no type given"
Unknown:{prefix}Legend is connected to PC:{prefix}LegendPC
	""".format(prefix=secrets.token_hex(16)).split("\n")

def main(tree, output_filename):
	dot = Digraph(graph_attr = {'splines':'ortho', 'strict': 'false', 'overlap': 'false'})
	#dot = Digraph(graph_attr = {"concentrate": "true", 'strict': 'false', 'overlap': 'false'})

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
		"router": "diamond",
		"switch": "invtriangle",
		"laptop": "box3d",
		"pc": "box3d",
		"phone": "box3d",
		"virtualmachine": "circle",
		"location": "house",
		"unknown": "doublecircle"
	}

	for row in proper_tree:
		with dot.subgraph() as sub:
			try:
				shape_a = symbol_shapes[data[row['Name A']]['meta']['Type'].lower().replace("virtual_machine", "virtualmachine").replace("virtual machine", "virtualmachine")]
			except KeyError:
				shape_a = symbol_shapes['unknown']

			try:
				meta_details = data[row['Name A']]['meta'].copy()
				try:
					meta_details['Blurb']
					del meta_details['Blurb']
				except KeyError:
					pass
				details_a = json.dumps(meta_details, indent=4, sort_keys=True)[1:-1]
			except KeyError:
				details_a = ''

			try:
				shape_b = symbol_shapes[data[row['Name B']]['meta']['Type'].lower()]
			except KeyError:
				shape_b = symbol_shapes['unknown']

			try:
				meta_details = data[row['Name B']]['meta'].copy()
				try:
					meta_details['Blurb']
					del meta_details['Blurb']
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
				"ethernet": "blue",
				"wifi": "green",
				"physical": "black",
				"other": "grey"
			}

			try:
				color_a = colour_scheme[data[row['Name A']]['relations'][0]['kind'].lower()]
			except (IndexError, KeyError):
				color_a = colour_scheme['other']

			label_a = label_a + blurb_a + "\n" + details_a
			label_b = label_b + blurb_b + "\n" + details_b

			sub.node(name=idents[row['Name A']])
			sub.node(idents[row['Name A']], label=label_a, tooltip = details_a, shape = shape_a, fillcolor = "red")

			sub.node(name=idents[row['Name B']])
			sub.node(idents[row['Name B']], label=label_b, tooltip = details_b, shape = shape_b, fillcolor = "red")

			if idents[row['Name A']] == idents[row['Name B']]:
				sub.edge(idents[row['Name A']] + ":sw", idents[row['Name B']].split(":", 1)[0], color=color_a)
			else:
				sub.edge(idents[row['Name A']], idents[row['Name B']].split(":", 1)[0], color=color_a)

	p = pathlib.Path(output_filename)
	dot.format = p.suffix[1:]
	dot.render(p.stem)

def cli():
	import argparse
	parser = argparse.ArgumentParser(description='Render a network tree.')
	parser.add_argument('-i', '--input-file', help='The input file to parse.', required=True)
	parser.add_argument('-o', '--output-file', help='The output file to render.', required=True)

	args = parser.parse_args()

	tree = parse_file(args.input_file)
	main(tree, args.output_file)

if __name__ == "__main__":
	cli()
