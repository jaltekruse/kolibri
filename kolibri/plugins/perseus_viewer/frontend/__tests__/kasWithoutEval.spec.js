import { parse } from '@khanacademy/kas';

// Kolibri's Content Security Policy has no 'unsafe-eval', so browsers refuse new Function,
// which KAS uses to compile the expressions in exercises such as interactive graphs.
// patches/@khanacademy__kas@2.2.3.patch makes it evaluate the expressions instead.
function compileWithoutEval(expression, options) {
  const RealFunction = global.Function;
  let refused = false;
  global.Function = function () {
    refused = true;
    throw new EvalError(
      "Refused to evaluate a string as JavaScript because 'unsafe-eval' is not an allowed source of script",
    );
  };
  try {
    const compiled = parse(expression, options).expr.compile();
    expect(refused).toBe(true);
    return compiled;
  } finally {
    global.Function = RealFunction;
  }
}

function compile(expression, options) {
  return parse(expression, options).expr.compile();
}

describe('KAS expressions where eval is refused', () => {
  it('evaluates numbers and variables', () => {
    expect(compileWithoutEval('-8')({})).toBe(-8);
    expect(compileWithoutEval('4x-2')({ x: 3 })).toBe(10);
  });

  it('calls functions passed in as JavaScript functions, as Perseus passes them', () => {
    const vars = { x: 2, f: x => x * 10 };

    expect(compileWithoutEval('f(x)+1', { functions: ['f'] })(vars)).toBe(21);
  });

  it('gives the results the compiled code gives', () => {
    const vars = { x: 1.5, y: -2 };
    for (const expression of ['3x^2-2y', 'sin(x)+cos(y)', 'abs(y)/x', 'ln(x)', 'pi*x']) {
      expect(compileWithoutEval(expression)(vars)).toBeCloseTo(compile(expression)(vars));
    }
  });
});
