output "budget_name" {
  description = "Nom du budget."
  value       = aws_budgets_budget.monthly.name
}
