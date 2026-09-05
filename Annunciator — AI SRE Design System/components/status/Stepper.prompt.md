Remediation progress: six flush 3px segments, green behind, amber at the cursor, border grey ahead.

```jsx
<Stepper current={3} labels={["DETECT","TRIAGE","DIAGNOSE","APPROVE","EXECUTE","VERIFY"]} />
<Stepper current={4} failed />
```

Gaps never exceed 3px so it reads as one bar. failed replaces the remaining run with a single red segment rather than marking one step red.
