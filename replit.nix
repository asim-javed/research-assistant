{ pkgs }: {
  deps = [
    pkgs.gitleaks
    pkgs.python311Full
    pkgs.nodejs
    pkgs.pipenv
  ];
}
