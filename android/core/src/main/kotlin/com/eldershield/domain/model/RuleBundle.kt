package com.eldershield.domain.model

data class CountryRestriction(
    val id: String,
    val name: String,
    val countries: List<String>,
    val applyTo: List<String>,
    val enabled: Boolean,
    val version: Int,
    val description: String? = null,
)

data class RuleBundle(
    val version: Int,
    val countryRestrictions: List<CountryRestriction> = emptyList(),
    val callRules: List<Map<String, Any?>> = emptyList(),
    val appRiskRules: List<Map<String, Any?>> = emptyList(),
    val updatedAt: String? = null,
)
