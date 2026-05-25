# Emergency Dispatch Router
### AI Project — A* + BFS Pathfinding

A visual emergency dispatch system using A* Search and BFS on a synthetic city road network.

---

## Setup

```bash
# 1. Install dependencies
pip install flask networkx

# 2. Run the app
python app.py

# 3. Open in browser
http://localhost:5050
```

---

## How to Use

| Action | How |
|--------|-----|
| Set emergency location | Click **📍 Emergency** mode → click any node on map |
| Block roads | Click **🚧 Block Road** mode → click nodes to toggle |
| Find best route | Click **⚡ DISPATCH AMBULANCE** |
| View alternate routes | Click any result card in the sidebar |

---

## Algorithms

### BFS (Breadth-First Search)
- Explores all reachable hospitals from the emergency node
- Used for reachability check when roads are blocked
- Unweighted — finds minimum hops first

### A* Search
- Finds the shortest-cost (distance) path to each reachable hospital
- Heuristic: straight-line (Euclidean) distance to goal
- Returns cost in metres and estimated arrival time

---

## Project Structure

```
emergency_dispatch/
├── app.py              ← Flask server + BFS + A* algorithms
├── templates/
│   └── index.html      ← Full UI with canvas map
└── README.md
```

---

## City Graph

- 10×10 grid of 100 nodes (intersections)
- ~376 road edges with randomised travel weights
- 5 hospitals at fixed locations
- Diagonal shortcuts added for realism
- Coordinates centred on Islamabad, Pakistan
