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

data class CallRule(
    val id: String,
    val countryCodes: List<String> = emptyList(),
    val whitelist: List<String> = emptyList(),
    val enabled: Boolean = true,
    val version: Int = 1,
)

data class RuleBundle(
    val version: Int,
    val countryRestrictions: List<CountryRestriction> = emptyList(),
    val callRules: List<CallRule> = emptyList(),
    val appRiskRules: List<Map<String, Any?>> = emptyList(),
    val updatedAt: String? = null,
)
