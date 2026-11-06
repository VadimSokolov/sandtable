# Mission Viewer V3 run guide

## Start the viewer

If the viewer server is already running, refresh the page. To start the server, use the repository's existing virtual environment.

```bash
cd "/Users/markfahim/Work/GRA GM/sandtable"
PYTHONPATH=src .venv/bin/python -m sandtable.mission_viewer --port 8767
```

Leave the server running in the terminal and visit [Mission Viewer V3](http://127.0.0.1:8767/) in your browser.

## Edit a road and calculate the route

1. Open **Build map**. Under **Edit the map**, use **Choose a road to edit**.
2. Click **Set my score** and enter a value from 0 to 100 in **Your score**. For example, set **R7 · JUNCTION ↔ LOWER_W** to **60**. Use **Use map estimate** to return a road to its calculated score.
3. Once your road edits are ready, click **Update route using this score**. The planner uses the full draft, including edits to other roads, and chooses the path with the lowest total cost.
4. Read the node sequence and total cost under **Chosen path**. Open **Road graph & costs** to see the edge costs and follow the selected path in green.

The planner adds up every edge on each path. Lowering the score of **R4 · JUNCTION ↔ UPPER_W** lowers the cost of that edge. The upper route also includes **R5** and **R6**, so the lower route can still have the smaller total.

## Use a fixed path

To test the upper route on the sketch, select **Upper loop** in **Route planner**, then click **Validate & review**. This prepares the chosen path for the mission. **Update route using this score** switches back to automatic route selection.

## Run and replay the mission

1. Click **Run new Python mission** after calculating the automatic path or validating the fixed path.
2. In **Run & inspect**, wait for the Python job to finish.
3. Click **Play** to watch the convoy. Use the timeline or frame controls to inspect individual moments.

See the [viewer README](../../studies/convoy-study/mission-viewer-v3/README.md) for more launch options.
