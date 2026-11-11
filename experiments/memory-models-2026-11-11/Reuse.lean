@[extern "audit_lean_start"] opaque auditStart : IO Unit
@[extern "audit_lean_stop"] opaque auditStop (keep : List Nat) (checksum : UInt64) : IO Unit

@[noinline] def transform : List Nat → List Nat
  | [] => []
  | x :: xs => (x + 1) :: transform xs

@[noinline] def checksum (xs : List Nat) : UInt64 := (xs.foldl (· + ·) 0).toUInt64

@[noinline] def runCase (retained : Bool) (n : Nat) : IO Unit := do
  let xs := List.range n
  auditStart
  if retained then
    auditStop xs (checksum (transform xs))
  else
    auditStop [] (checksum (transform xs))

def main : IO Unit := do
  runCase false 1000
  runCase true 1000
