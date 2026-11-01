import networkx as nx
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models import Concept, ConceptPrerequisite, ConceptMastery

def build_concept_graph(db: Session) -> nx.DiGraph:
    """
    Constructs a NetworkX Directed Acyclic Graph (DAG) of the curriculum
    from database concepts and prerequisite relationships.
    """
    graph = nx.DiGraph()
    concepts = db.query(Concept).all()
    for c in concepts:
        graph.add_node(
            c.id,
            title=c.title,
            description=c.description,
            category=c.category,
            order_index=c.order_index
        )

    prereqs = db.query(ConceptPrerequisite).all()
    for p in prereqs:
        graph.add_edge(p.parent_id, p.child_id)

    return graph

def get_concept_graph_data(db: Session, learner_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns graph representation with nodes, edges, acyclic verification,
    and overlays the learner's live mastery scores on each node.
    """
    graph = build_concept_graph(db)
    concepts = db.query(Concept).order_index = Concept.order_index
    concepts = db.query(Concept).order_by(Concept.order_index).all()
    prereqs = db.query(ConceptPrerequisite).all()

    # Fetch learner's mastery if provided
    mastery_map = {}
    if learner_id:
        records = db.query(ConceptMastery).filter(ConceptMastery.learner_id == learner_id).all()
        for r in records:
            mastery_map[r.concept_id] = {
                "score": r.mastery_score,
                "attempts": r.total_attempts,
                "correct": r.correct_attempts,
                "status": "mastered" if r.mastery_score >= 75 else ("developing" if r.mastery_score >= 40 else "gap")
            }

    nodes = []
    for c in concepts:
        m = mastery_map.get(c.id, {"score": 0.0, "attempts": 0, "correct": 0, "status": "unattempted"})
        predecessors = list(graph.predecessors(c.id))
        successors = list(graph.successors(c.id))

        nodes.append({
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "category": c.category,
            "order_index": c.order_index,
            "mastery_score": round(m["score"], 1),
            "attempts": m["attempts"],
            "correct": m["correct"],
            "status": m["status"],
            "prerequisites": predecessors,
            "unlocks": successors
        })

    edges = [{"parent_id": p.parent_id, "child_id": p.child_id} for p in prereqs]

    return {
        "nodes": nodes,
        "edges": edges,
        "is_acyclic": nx.is_directed_acyclic_graph(graph),
        "topological_order": list(nx.topological_sort(graph)) if nx.is_directed_acyclic_graph(graph) else []
    }

def find_weak_prerequisites(db: Session, learner_id: str, concept_id: str) -> List[Dict[str, Any]]:
    """
    Identifies any prerequisite concepts where learner mastery is below 50%.
    """
    graph = build_concept_graph(db)
    if concept_id not in graph:
        return []

    ancestors = nx.ancestors(graph, concept_id)
    if not ancestors:
        return []

    masteries = db.query(ConceptMastery).filter(
        ConceptMastery.learner_id == learner_id,
        ConceptMastery.concept_id.in_(ancestors)
    ).all()

    mastery_dict = {m.concept_id: m.mastery_score for m in masteries}
    weak_prereqs = []

    for anc_id in ancestors:
        score = mastery_dict.get(anc_id, 0.0)
        if score < 50.0:
            c = db.query(Concept).filter(Concept.id == anc_id).first()
            if c:
                weak_prereqs.append({
                    "concept_id": c.id,
                    "title": c.title,
                    "mastery_score": round(score, 1)
                })

    return weak_prereqs
