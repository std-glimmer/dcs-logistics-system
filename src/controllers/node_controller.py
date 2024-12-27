from typing import Dict, List, Optional
from ..models.node import Node
from ..utils.json_handler import JSONHandler
from ..services.logger import LoggerService

class NodeController:
    def __init__(self, structure_file: str, logger : LoggerService):
        self.nodes: Dict[str, Node] = {}
        self.structure_file = structure_file
        self.hierarchy: Dict[str, List[str]] = {}
        self.logger = logger
        self.load_structure()

    def load_structure(self) -> None:
        json_handler = JSONHandler(self.structure_file)
        structure_data = json_handler.read_json()
        
        def process_node(node_data, parent_name: Optional[str] = None):
            node = Node.from_json(node_data)
            self.nodes[node.name] = node
            
            if parent_name:
                if parent_name not in self.hierarchy:
                    self.hierarchy[parent_name] = []
                self.hierarchy[parent_name].append(node.name)
            
            if "children" in node_data:
                for child in node_data["children"]:
                    process_node(child, node.name)

        for node_data in structure_data["nodes"]:
            process_node(node_data)

    def get_node(self, name: str) -> Optional[Node]:
        return self.nodes.get(name)

    def get_children(self, node_name: str) -> List[Node]:
        if node_name not in self.hierarchy:
            return []
        return [self.nodes[name] for name in self.hierarchy[node_name]]

    def get_all_nodes(self) -> List[Node]:
        return list(self.nodes.values())

    def apply_daily_consumption(self) -> None:
        """Apply daily consumption to all nodes and log warnings"""
        for node in self.nodes.values():
            warnings = node.apply_consumption()
            if warnings:
                self.logger.warning(f"Low resources at {node.name}: {', '.join(warnings)}")

    def save_structure(self) -> None:
        def build_node_data(node_name: str) -> dict:
            node = self.nodes[node_name]
            node_data = node.to_json()
            
            if node_name in self.hierarchy:
                node_data["children"] = [
                    build_node_data(child_name) 
                    for child_name in self.hierarchy[node_name]
                ]
            else:
                node_data["children"] = []
            return node_data

        root_nodes = [
            name for name, node in self.nodes.items()
            if node.node_type == "airbase"
        ]
        
        structure_data = {
            "nodes": [build_node_data(name) for name in root_nodes]
        }
        
        json_handler = JSONHandler(self.structure_file)
        json_handler.write_json(structure_data)

    def print_graph(self) -> None:
        """Print ASCII visualization of the node graph structure with warnings"""
        
        def get_node_status(node: Node) -> tuple:
            """Get node status and warnings"""
            warnings = []
            for resource in ['fuel', 'ammo']:
                if node.state[resource] <= 0:
                    warnings.append(f"NO {resource.upper()}")
                elif node.consumption[resource] > 0:
                    days = node.state[resource] / node.consumption[resource]
                    if days <= node.WARNING_DAYS:
                        warnings.append(f"{resource}: {days:.1f}d")
            return warnings

        def print_node(node_name: str, level: int = 0):
            node = self.nodes[node_name]
            indent = "    " * level
            branch = "└──" if level > 0 else ""
            
            # Format resources info
            resources = f"[F:{node.state['fuel']}/A:{node.state['ammo']}]"
            
            # Get warnings
            warnings = get_node_status(node)
            warning_text = f" <!> {', '.join(warnings)}" if warnings else ""
            
            # Add emergency indicator
            emergency = " [!EMERGENCY!]" if node.emergency_mode else ""
            
            # Format node info
            node_info = f"{node.node_type}: {node.name} {resources}{emergency}{warning_text}"
            
            print(f"{indent}{branch}{node_info}")
            
            # Print children recursively
            if node_name in self.hierarchy:
                for child in self.hierarchy[node_name]:
                    print_node(child, level + 1)

        print("\nLogistics Network Structure:")
        print("==========================")
        root_nodes = [name for name, node in self.nodes.items() 
                    if node.node_type == "airbase"]
        for root in root_nodes:
            print_node(root)
        print("==========================\n")