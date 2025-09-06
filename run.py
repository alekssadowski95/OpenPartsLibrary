import os
import pandas as pd
import uuid

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier, File, Component, ComponentComponent


# Initialize the parts library
pl = PartsLibrary()

# Clear the parts library
os.system('cls')
pl.delete_all()

# Get the paths for this project
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA_DIR = os.path.join(PROJECT_DIR, "openpartslibrary", "sample")
LIBRARY_DATA_DIR = os.path.join(PROJECT_DIR, "openpartslibrary", "data")
LIBRARY_DATA_FILES_DIR = os.path.join(LIBRARY_DATA_DIR, "files")

# Load file and original name, change name to uuid and save it in the data/files dir
# ..
file_1_path = os.path.join(SAMPLE_DATA_DIR, 'M6x12-Screw.FCStd')
file_1_uuid = str(uuid.uuid4())
file_1_name = os.path.basename(file_1_path)
file_1_ext = os.path.splitext(file_1_path)[1]  # includes the dot
with open(file_1_path, "rb") as src_file:   # read in binary mode
    data = src_file.read()
    dst_path = os.path.join(LIBRARY_DATA_FILES_DIR, file_1_uuid + file_1_ext)
    with open(dst_path, "wb") as dst_file:   # write in binary mode
        dst_file.write(data)
# Create a new file
file_1 = File(uuid = file_1_uuid, name = file_1_name, description = 'This is a CAD file.')

# Load file and original name, change name to uuid and save it in the data/files dir
# ..
file_2_path = os.path.join(SAMPLE_DATA_DIR, 'M6x20-Screw.FCStd')
file_2_uuid = str(uuid.uuid4())
file_2_name = os.path.basename(file_2_path)
file_2_ext = os.path.splitext(file_2_path)[1]  # includes the dot
with open(file_2_path, "rb") as src_file:   # read in binary mode
    data = src_file.read()
    dst_path = os.path.join(LIBRARY_DATA_FILES_DIR, file_2_uuid + file_2_ext)
    with open(dst_path, "wb") as dst_file:   # write in binary mode
        dst_file.write(data)
# Create a new file
file_2 = File(uuid = file_2_uuid, name = file_2_name, description = 'This is a CAD file.')

# Load file and original name, change name to uuid and save it in the data/files dir
# ..
file_3_path = os.path.join(SAMPLE_DATA_DIR, 'M6x35-Screw.FCStd')
file_3_uuid = str(uuid.uuid4())
file_3_name = os.path.basename(file_3_path)
file_3_ext = os.path.splitext(file_3_path)[1]  # includes the dot
with open(file_3_path, "rb") as src_file:   # read in binary mode
    data = src_file.read()
    dst_path = os.path.join(LIBRARY_DATA_FILES_DIR, file_3_uuid + file_3_ext)
    with open(dst_path, "wb") as dst_file:   # write in binary mode
        dst_file.write(data)
# Create a new file
file_3 = File(uuid = file_3_uuid, name = file_3_name, description = 'This is a CAD file.')

# Create a new part
part_1 = Part(
            uuid = str(uuid.uuid4()),
            number='SCRW-2001',
            name='Screw ISO 4762 M6x12',
            description='A hexagon socket head cap screw for fastening metal parts',
            revision="1",
            lifecycle_state="In Work",
            owner='Max Mustermann',
            material='Steel',
            mass=0.03,
            dimension_x=0.02,
            dimension_y=0.005,
            dimension_z=0.005,
            quantity=100,
            attached_documents_reference='DOCUMENTS REFERENCE',
            lead_time=10,
            make_or_buy='make',
            manufacturer_number='MFN-100001',
            unit_price=0.10,
            currency='EUR',
            cad_reference = file_1
)

# Create a new part
part_2 = Part(
            uuid = str(uuid.uuid4()),
            number='SCRW-2002',
            name='Screw ISO 4762 M6x20',
            description='A hexagon socket head cap screw for fastening metal parts',
            revision="1",
            lifecycle_state="In Work",
            owner="Portland Bolt",
            material='Stainless Steel',
            mass=0.05,
            dimension_x=0.03,
            dimension_y=0.01,
            dimension_z=0.01,
            quantity=150,
            attached_documents_reference='DOCUMENTS REFERENCE BOLT',
            lead_time=7,    
            make_or_buy='buy',
            manufacturer_number='PB-2002',
            unit_price=0.15,    
            currency='EUR',
            cad_reference = file_2
)

# Create a new part
part_3 = Part(
            uuid = str(uuid.uuid4()),
            number='SCRW-2003',
            name='Screw ISO 4762 M6x35',
            description='A hexagon socket head cap screw for fastening metal parts',
            revision="1",
            lifecycle_state="In Work",
            owner="Grainger",
            material='Brass',
            mass=0.02,
            dimension_x=0.015,
            dimension_y=0.007,
            dimension_z=0.007,
            quantity=300,
            attached_documents_reference='DOCUMENTS REFERENCE HEX NUT',
            lead_time=4,
            make_or_buy='buy',
            manufacturer_number='GN-4004',
            unit_price=0.18,
            currency='EUR',
            cad_reference = file_3
)

# Add a all created parts to the parts library
pl.session.add(part_1)
pl.session.add(part_2)
pl.session.add(part_3)
pl.session.commit()

# Create a new supplier
supplier_1 = Supplier(
                uuid = str(uuid.uuid4()),
                name = 'Adolf Würth GmbH & Co. KG',
                description = 'The Würth Group is a leader in the development, manufacture, and distribution of assembly and fastening materials. The globally active family-owned company, headquartered in Künzelsau, Germany, comprises over 400 subsidiaries with over 2,800 branches in 80 countries.',
                street = 'Reinhold-Würth-Straße',
                house_number = '12',
                postal_code = '74653',
                city = 'Künzelsau-Gaisbach',
                country = 'Deutschland'
)

# Create a new supplier
supplier_2 = Supplier(
                uuid = str(uuid.uuid4()),
                name = 'Robert Bosch GmbH',
                description = 'The Bosch Group is a leading international supplier of technology and services with approximately 418,000 associates worldwide (as of December 31, 2024).',                        
                street = 'Robert-Bosch-Platz',
                house_number = '1',
                postal_code = '70839',
                city = 'Gerlingen-Schillerhöhe',
                country = 'Deutschland'
)

# Add a all created parts to the parts library
pl.session.add(supplier_1)
pl.session.add(supplier_2)
supplier_1.parts.append(part_1)
supplier_1.parts.append(part_2)
supplier_2.parts.append(part_3)
pl.session.commit()

# Create a new component and add it to the library
component_1 = Component(uuid = str(uuid.uuid4()), part = part_1, name = part_1.name)
component_2 = Component(uuid = str(uuid.uuid4()), part = part_2, name = part_2.name)
component_3 = Component(uuid = str(uuid.uuid4()), part = part_3, name = part_3.name)
component_4 = Component(uuid = str(uuid.uuid4()), name = 'Screw assembly')
pl.session.add(component_1)
pl.session.add(component_2)
pl.session.add(component_3)
pl.session.add(component_4)
pl.session.commit()

component_4.children.append(component_1)
component_4.children.append(component_2)
component_4.children.append(component_3)
pl.session.commit()

print('************************************************************') 
print('*  OpenPartsLibrary                                        *')
print('*  Aleksander Sadowski,  Nandana Gopala Krishnan (C) 2025  *')
print('************************************************************') 
pl.display()

component_relationships = pl.session.query(ComponentComponent).all()
for component_relationship in component_relationships:
    print(component_relationship)

import networkx as nx

# Query all relationships
relationships = pl.session.query(ComponentComponent).all()

# Build directed graph
G = nx.DiGraph()

for rel in relationships:
    parent = pl.session.query(Component).filter_by(id=rel.parent_component_id).first()
    child = pl.session.query(Component).filter_by(id=rel.child_component_id).first()

    if parent and child:
        G.add_node(parent.id, name=parent.name)
        G.add_node(child.id, name=child.name)
        G.add_edge(child.id, parent.id)

print(G)

import matplotlib.pyplot as plt

"""
Visualizes the directed graph with node labels as UUIDs.
"""
plt.figure(figsize=(10, 8))

pos = nx.spring_layout(G, seed=42)  # layout positions for nodes
labels = nx.get_node_attributes(G, 'name')

nx.draw(G, pos, with_labels=True, labels=labels, node_size=1500,
        node_color="skyblue", font_size=10, font_weight="bold",
        arrowsize=20, arrowstyle="->")

plt.title("Component Hierarchy Graph (Parent → Child)")
plt.show()

# Convert NetworkX graph to Cytoscape.js format
cy_data = {"nodes": [], "edges": []}

for node_id, attrs in G.nodes(data=True):
    cy_data["nodes"].append({
        "data": {
            "id": str(node_id), 
            "label": attrs.get("name", str(node_id))
        }
    })

for source, target in G.edges():
    cy_data["edges"].append({
        "data": {
            "source": str(source), 
            "target": str(target)
        }
    })

import json

# Create a self-contained HTML string
html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>NetworkX Graph</title>
<script src="https://unpkg.com/cytoscape/dist/cytoscape.min.js"></script>
</head>
<body style="width: 100vw; height: 100vh; margin: 0; padding: 0;">
    <div id="cy" style="width: 100%; height: 100%; margin: 0; padding: 0;"></div>
    <script>
    var cyData = {json.dumps(cy_data)};
    
    var cy = cytoscape({{
        container: document.getElementById('cy'),
        elements: cyData.nodes.concat(cyData.edges),
        style: [
            {{ 
                selector: 'node', 
                style: {{
                    'label': 'data(label)',
                    'background-color': '#1f78b4',
                    'color': '#000',               // label text color
                    'text-valign': 'top',          // vertical alignment outside the node
                    'text-halign': 'center',       // horizontal alignment
                    'text-margin-y': -10,          // offset above the node
                    'text-margin-x': 0,
                    'font-size': '12px',
                }}
            }},
            {{ 
                selector: 'edge', 
                style: {{
                    'width': 2,
                    'line-color': '#555',
                    'target-arrow-color': '#555',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier'
                }}
            }}
        ],
        layout: {{
            name: 'breadthfirst',
            directed: true,
            padding: 10
        }}
    }});
    </script>
</body>
</html>
"""

# Save HTML to file
with open(os.path.join(LIBRARY_DATA_FILES_DIR, "graph-" + str(uuid.uuid4()) + ".html"), "w") as f:
    f.write(html_content)


''' CLI to be moved to its own object OpenPartsLibraryCLI in cli.py
'''
'''
command_history = []
while True:    
    os.system('cls')
    print('************************************************************') 
    print('*  OpenPartsLibrary                                        *')
    print('*  Aleksander Sadowski,  Nandana Gopala Krishnan (C) 2025  *')
    print('************************************************************') 
    pl.display()
    commands = 'add part', 'add supplier', 'modify part', 'modify supplier', 'remove part', 'remove supplier'
    commands_str = ''
    for command in commands:
        commands_str = commands_str + '[' + str(command) + '] '
    print('Commands: ' + commands_str)
    print('Last commands:' + str([command for command in command_history][-5:]))
    input_cmd = input('Enter command: ')
    command_history.append(input_cmd)
    if input_cmd in commands:
        if input_cmd == 'add part':
            pass
        if input_cmd == 'add supplier':
            pass
        if input_cmd == 'modify part':
            os.system('cls')
            print('************************************************************') 
            print('*  OpenPartsLibrary                                        *')
            print('*  Aleksander Sadowski,  Nandana Gopala Krishnan (C) 2025  *')
            print('************************************************************')
            pl.display_parts()
            selected_part = int(input('Enter part id: '))
            pass
        if input_cmd == 'modify supplier':
            os.system('cls')
            print('************************************************************') 
            print('*  OpenPartsLibrary                                        *')
            print('*  Aleksander Sadowski,  Nandana Gopala Krishnan (C) 2025  *')
            print('************************************************************')
            print()
            pl.display_suppliers()
            selected_part = int(input('Enter supplier id: '))
            pass
        if input_cmd == 'remove part':
            pass
        if input_cmd == 'remove supplier':
            pass
'''