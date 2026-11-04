"""Run with python -m sandtable.mission_viewer [--port 8767]."""

import argparse, os
from .paths import ViewerPaths
from .storage import JobRepository
from .jobs import JobManager
from .application import ViewerApplication
from .http import ViewerHttpServer


def main():
    parser = argparse.ArgumentParser(description="Sandtable map builder and mission viewer")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--home", help="Runtime data and scenario library directory")
    args = parser.parse_args()
    paths = ViewerPaths.discover(args.home)
    os.environ["SANDTABLE_VIEWER_HOME"] = str(paths.home)
    repository = JobRepository(paths.data)
    jobs = JobManager(repository)
    jobs.reconcile()
    server = ViewerHttpServer(("127.0.0.1", args.port), ViewerApplication(paths, repository, jobs))
    print(f"Mission Viewer V3: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        jobs.close()
        server.server_close()


if __name__ == "__main__":
    main()
