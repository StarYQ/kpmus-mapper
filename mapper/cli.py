import sys

from mapper.db import DATABASE_URL, init_db
from mapper.manual import seed_team_aliases


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if (argv[:1] != ["init-db"]):
        print("usage: python -m mapper init-db [--reset]", file=sys.stderr)
        return 2
    init_db(reset=("--reset" in argv[1:]))
    print(f"tables ready: {DATABASE_URL.rsplit('@', 1)[-1]}; team aliases seeded: {seed_team_aliases()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
