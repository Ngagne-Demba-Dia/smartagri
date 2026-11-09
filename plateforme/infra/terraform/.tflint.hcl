# Configuration TFLint commune aux modules et environnements.
# Usage : tflint --init && tflint --recursive --config "$(pwd)/.tflint.hcl"

config {
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

# Version à vérifier et à épingler sur la dernière publication avant usage.
plugin "aws" {
  enabled = true
  version = "0.34.0"
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
}

rule "terraform_naming_convention" {
  enabled = true
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_unused_declarations" {
  enabled = true
}
