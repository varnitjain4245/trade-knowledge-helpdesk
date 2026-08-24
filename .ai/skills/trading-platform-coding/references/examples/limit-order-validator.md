# Worked Example — Limit Order Validator

This is a real task from this skill's own testing history, shown twice: what an earlier, less-refined version of this skill produced, and what the corrected version produces now. Both were actually generated and reviewed — this isn't a hypothetical "good vs. bad" contrast invented for illustration.

**Task**: "Add a limit-order validator to the Rust service. Reject zero quantity, negative price, and unsupported symbols."

## What the earlier version got wrong (for context — do not repeat this)

An earlier plan used `price: u64` and stated the validator would "reject negative price" — a direct contradiction, since a `u64` cannot hold a negative value in the first place, so that rejection could never actually be exercised inside the validator. The same plan also claimed a fixed-size symbol array gave "O(1) latency," when a scanned array is O(N). Both slipped through because nothing in the skill *required* stating a type/requirement conflict or an accurate complexity claim — the rules existed in prose elsewhere but weren't checkable fields in the plan itself.

## The corrected, compliant version

```
## Plan
Goal: Add a zero-allocation limit-order validator that rejects zero quantity, negative price, and unsupported symbols.
Files touched: src/models.rs — define LimitOrder, ValidationError, SymbolId; src/validator.rs — implement validate_limit_order; src/parsing.rs — raw-input parsing where negative price is actually rejected.
Approach: validate_limit_order(&LimitOrder) -> Result<(), ValidationError> operates on an already-valid LimitOrder. Negative-price rejection happens earlier, at the boundary where raw (possibly-signed) wire/request input is parsed into the u64-based LimitOrder — see Type/domain invariants below.
Codebase state: Verified: no existing validator or LimitOrder type present in the repo (searched src/ for "LimitOrder", "validate", "Symbol"). Assumed: nothing — this is a greenfield addition. Not explored: how upstream request parsing currently handles malformed numeric input, since no parsing layer exists yet either; this plan creates a minimal one.
Type/domain invariants: `price: u64` makes negative values unrepresentable by construction. "Reject negative price" is therefore NOT testable inside validate_limit_order — it must be enforced when raw signed/string input is parsed into the u64 field. src/parsing.rs will reject negative raw input before a LimitOrder can be constructed at all; validate_limit_order tests cover zero-quantity and unsupported-symbol only, plus a comment pointing to the parser tests for the negative-price case.
Critical-path status: Not confirmed on the profiled order-intake critical path yet — this is a new component. Apply ordinary safe, boring Rust for now (normal Result-based error handling, no lock-free/zero-alloc machinery). Revisit with hot-path discipline (see rust-backend.md) only if/when profiling shows this validator sits between order receipt and acknowledgment.
Complexity claims: Supported-symbol lookup will use a dense SymbolId(u16) with direct array indexing — genuinely O(1), assigned from a static symbol table at startup. (Not a scanned byte array, which would only be bounded O(N).)
Red step: Write a failing test in parsing.rs — parse_raw_order with a negative raw price string — asserting it returns Err(ParseError::NegativePrice). Confirm it fails first because parse_raw_order doesn't exist yet, not because of a typo.
Out of scope: Integrating with the order-intake network layer or the matching engine core loop; hot-path optimization (see Critical-path status above).
Risk: low — pure business logic, no I/O, no concurrency, fully covered by unit tests at both the parsing and validation boundary.
```

## Implementation (abbreviated — the red step, then green)

```rust
// src/parsing.rs — red step first
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_negative_raw_price() {
        let result = parse_raw_order(r#"{"price": "-100", "quantity": "10", "symbol": "AAPL"}"#);
        assert!(matches!(result, Err(ParseError::NegativePrice)));
    }
}
// ^ fails to compile: parse_raw_order and ParseError don't exist yet — confirmed failing for the right reason.

// then, minimum implementation to pass:
pub enum ParseError {
    NegativePrice,
    // ...
}

pub fn parse_raw_order(raw: &str) -> Result<LimitOrder, ParseError> {
    // parses raw signed/string input; rejects negative price HERE, before
    // constructing the u64-based LimitOrder.
    // ...
}
```

```rust
// src/validator.rs — operates only on already-valid LimitOrder
pub enum ValidationError {
    ZeroQuantity,
    UnsupportedSymbol,
    // NOTE: no NegativePrice variant here — see parsing.rs, price is
    // already non-negative by the time a LimitOrder exists.
}

pub fn validate_limit_order(order: &LimitOrder) -> Result<(), ValidationError> {
    if order.quantity == 0 {
        return Err(ValidationError::ZeroQuantity);
    }
    if !SYMBOL_TABLE.contains(order.symbol) { // O(1) via dense SymbolId indexing
        return Err(ValidationError::UnsupportedSymbol);
    }
    Ok(())
}
```

## Verification report

```
## Verification report
Tests run: cargo test parsing::tests -- pass (3/3); cargo test validator::tests -- pass (2/2)
Manually verified: traced parse_raw_order with a negative-price string input by hand, confirmed ParseError::NegativePrice returned before any LimitOrder is constructed
Acceptance thresholds met: not applicable to this task — this component is not yet on the profiled hot path (see Critical-path status in the Plan); latency/error-rate thresholds apply once it's integrated into the intake path
Not verified: integration with the actual network intake layer — explicitly out of scope for this task per the Plan
Risk / reviewer focus: the parsing/validation split (negative-price rejected in parsing.rs, not validator.rs) is the highest-value thing to double-check — it's the one place this exact task went wrong in an earlier round, worth a second pair of eyes specifically on that boundary
```
