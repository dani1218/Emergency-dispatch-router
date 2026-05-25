import os
import json
import math
import heapq
import random

from collections import deque
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# ── Synthetic city graph (no internet needed) ──────────────────────────────

# Grid of 10×10 intersections centred on Islamabad coords
BASE_LAT, BASE_LON = 33.720, 73.060
GRID = 10          # 10×10 = 100 nodes
SPACING = 0.008    # ~900 m between nodes


def build_city():
    nodes, edges = {}, []

    for r in range(GRID):
        for c in range(GRID):
            nid = r * GRID + c # Unique node ID

            lat = BASE_LAT + r * SPACING # Latitude increases as we go down the grid
            lon = BASE_LON + c * SPACING # Longitude increases as we go right in the grid

            nodes[nid] = {
                "lat": lat,
                "lon": lon,
                "id": nid
            }

    def dist(a, b):
        # find distance in meters between two nodes using their lat/lon
        dlat = nodes[a]["lat"] - nodes[b]["lat"]
        dlon = nodes[a]["lon"] - nodes[b]["lon"]

        return math.sqrt(dlat**2 + dlon**2) * 111_000

    adj = {n: [] for n in nodes} # use adjacency list for graph representation

    # Grid roads
    for r in range(GRID):
        for c in range(GRID):

            nid = r * GRID + c # Unique node ID
            #dr = change in row, dc = change in column
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                # Check if neighbor is within grid bounds

                nr, nc = r + dr, c + dc

                if 0 <= nr < GRID and 0 <= nc < GRID:

                    nb = nr * GRID + nc

                    w = dist(nid, nb) * random.uniform(0.8, 1.4)
                    # nb = neighbor node
                    # w = road distance/weight
                    adj[nid].append((nb, w))

                    edges.append({
                        "from": nid,
                        "to": nb,
                        "weight": round(w)
                    })

    # Random diagonal shortcuts
    for r in range(GRID - 1):
        for c in range(GRID - 1):

            nid = r * GRID + c
            nb = (r + 1) * GRID + (c + 1)

            if random.random() < 0.25:
                # Add diagonal edge with weight based on distance + random factor
                w = dist(nid, nb) * random.uniform(0.9, 1.2)
                # Add to both nodes' adjacency lists
                adj[nid].append((nb, w))
                adj[nb].append((nid, w))

                edges.append({
                    "from": nid,
                    "to": nb,
                    "weight": round(w)
                })

    return nodes, adj, edges


random.seed(42)

NODES, ADJ, EDGES = build_city()

# Fixed hospital locations
HOSPITAL_NODES = [5, 23, 67, 81, 44]

HOSPITAL_NAMES = [
    "City Hospital",
    "Central Medical",
    "North Clinic",
    "South Care",
    "East Emergency"
]


# ── BFS ─────────────────────────────────────────────────────────────────────

def bfs(start, targets):

    visited = {start}
    queue = deque([start])

    parent = {start: None}

    order = []
    found = {}

    while queue:

        node = queue.popleft()

        order.append(node)

        if node in targets and node not in found:
            found[node] = node

        for item in ADJ[node]:

            nb = item[0] # Neighbor node ID
            weight = item[1] # Edge weight
            if nb not in visited:

                visited.add(nb)

                parent[nb] = node

                queue.append(nb)

    # Reconstruct paths
    paths = {}

    for h in found:

        path = []
        cur = h

        while cur is not None:

            path.append(cur)

            cur = parent.get(cur)

        paths[h] = list(reversed(path))

    return order, paths


# ── A* ──────────────────────────────────────────────────────────────────────

def heuristic(a, b):
    # Use straight-line distance (Haversine formula approximation) as heuristic
    la, loa = NODES[a]["lat"], NODES[a]["lon"] # Latitude and longitude of node a
    lb, lob = NODES[b]["lat"], NODES[b]["lon"] # Latitude and longitude of node b
# Convert lat/lon differences to meters (approximation)
    return math.sqrt((la - lb)**2 + (loa - lob)**2) * 111_000


def astar(start, goal):

    open_set = [(0, start)]

    came_from = {}

    g = {start: 0}

    f = {start: heuristic(start, goal)}

    visited_order = []

    closed = set()

    while open_set:

        _, cur = heapq.heappop(open_set)

        if cur in closed:
            continue

        closed.add(cur)

        visited_order.append(cur)

        if cur == goal:

            path = [cur]

            while cur in came_from:

                cur = came_from[cur]

                path.append(cur)

            path.reverse()

            return path, round(g[goal]), visited_order

        for nb, w in ADJ[cur]:

            if nb in closed:
                continue

            tentative = g[cur] + w

            if tentative < g.get(nb, float("inf")):

                came_from[nb] = cur

                g[nb] = tentative

                f[nb] = tentative + heuristic(nb, goal)

                heapq.heappush(open_set, (f[nb], nb))

    return [], float("inf"), visited_order


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/map_data")
def map_data():

    node_list = [
        {
            "id": n,
            "lat": d["lat"],
            "lon": d["lon"]
        }
        for n, d in NODES.items()
    ]

    hospital_list = [
        {
            "id": HOSPITAL_NODES[i],
            "name": HOSPITAL_NAMES[i]
        }
        for i in range(len(HOSPITAL_NODES))
    ]

    return jsonify({
        "nodes": node_list,
        "edges": EDGES,
        "hospitals": hospital_list,
        "base": {
            "lat": BASE_LAT + GRID * SPACING / 2,
            "lon": BASE_LON + GRID * SPACING / 2
        }
    })


@app.route("/api/dispatch", methods=["POST"])
def dispatch():

    data = request.json

    emergency = int(data.get("emergency_node", 0))

    blocked = set(int(x) for x in data.get("blocked", []))

    # Emergency node blocked
    if emergency in blocked:

        return jsonify({
            "error": "Emergency node is blocked"
        }), 400

    # Ignore blocked hospitals
    targets = set(HOSPITAL_NODES) - blocked

    # Save original graph
    saved = {}

    for node in ADJ:
        saved[node] = ADJ[node][:]

    # Completely remove blocked nodes
    for b in blocked:
        ADJ[b] = []

    # Remove all edges leading TO blocked nodes
    for node in ADJ:

        ADJ[node] = [
            (nb, w)
            for nb, w in ADJ[node]
            if nb not in blocked
        ]

    # Run BFS
    bfs_order, bfs_paths = bfs(emergency, targets)

    reachable = list(bfs_paths.keys())

    results = []

    # Run A*
    for h in reachable:

        path, cost, astar_order = astar(emergency, h)

        idx = HOSPITAL_NODES.index(h)

        results.append({
            "hospital_id": h,
            "hospital_name": HOSPITAL_NAMES[idx],
            "path": path,
            "cost_m": cost,
            "cost_min": round(cost / 10_000 * 6, 1),
            "astar_explored": astar_order
        })

    # Sort by shortest distance
    results.sort(key=lambda x: x["cost_m"])

    best = results[0] if results else None

    # Restore original graph
    for node in saved:
        ADJ[node] = saved[node]

    return jsonify({
        "emergency": emergency,
        "blocked": list(blocked),
        "bfs_order": bfs_order[:60],
        "bfs_paths": {
            str(k): v for k, v in bfs_paths.items()
        },
        "results": results,
        "best": best
    })


# ── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5050)