# Analysis results for test-filename.sol

## Unchecked Call Return Value
- SWC ID: 104
- Severity: Low
- Contract: Unknown
- Function name: `_function_0x141f32ff`
- PC address: 618
- Estimated Gas Usage: 1113 - 35865

### Description

The return value of a message call is not checked.
External calls return a boolean value. If the callee contract halts with an exception, 'false' is returned and execution continues in the caller. It is usually recommended to wrap external calls into a require statement to prevent unexpected states.

## Use of callcode
- SWC ID: 111
- Severity: Medium
- Contract: Unknown
- Function name: `_function_0x141f32ff`
- PC address: 618
- Estimated Gas Usage: 389 - 1141

### Description

Use of callcode is deprecated.
The callcode method executes code of another contract in the context of the caller account. Due to a bug in the implementation it does not persist sender and value over the call. It was therefore deprecated and may be removed in the future. Use the delegatecall method instead.

## Unchecked Call Return Value
- SWC ID: 104
- Severity: Low
- Contract: Unknown
- Function name: `_function_0x9b58bc26`
- PC address: 849
- Estimated Gas Usage: 1170 - 35922

### Description

The return value of a message call is not checked.
External calls return a boolean value. If the callee contract halts with an exception, 'false' is returned and execution continues in the caller. It is usually recommended to wrap external calls into a require statement to prevent unexpected states.

## External Call To User-Supplied Address
- SWC ID: 107
- Severity: Medium
- Contract: Unknown
- Function name: `_function_0xeea4c864`
- PC address: 1038
- Estimated Gas Usage: 471 - 1223

### Description

A call to a user-supplied address is executed.
The callee address of an external message call can be set by the caller. Note that the callee can contain arbitrary code and may re-enter any function in this contract. Review the business logic carefully to prevent averse effects on thecontract state.

## Unchecked Call Return Value
- SWC ID: 104
- Severity: Low
- Contract: Unknown
- Function name: `_function_0xeea4c864`
- PC address: 1038
- Estimated Gas Usage: 1195 - 35947

### Description

The return value of a message call is not checked.
External calls return a boolean value. If the callee contract halts with an exception, 'false' is returned and execution continues in the caller. It is usually recommended to wrap external calls into a require statement to prevent unexpected states.
