from gopackshot_print.app import run_app

if __name__ == '__main__':
	# Ensure any required env defaults can be set here later if needed
	exit_code = run_app()
	raise SystemExit(int(exit_code) if isinstance(exit_code, int) else 0)
