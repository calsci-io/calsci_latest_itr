from math import acos, acosh, asin, asinh, atan, atan2, atanh, ceil, copysign, cos, cosh
from math import degrees, e, erf, erfc, exp, expm1, fabs, floor, fmod, frexp, gamma
from math import isfinite, isinf, isnan, ldexp, lgamma, log, log10, log2, pi, pow
from math import radians, sin, sinh, sqrt, tan, tanh, trunc


class CalculatorService:
    def __init__(self, storage):
        self.storage = storage
        self.ans = 0

    def _safe_globals(self):
        safe = {
            "__builtins__": {},
            "sin": sin,
            "cos": cos,
            "tan": tan,
            "asin": asin,
            "acos": acos,
            "atan": atan,
            "atan2": atan2,
            "sinh": sinh,
            "cosh": cosh,
            "tanh": tanh,
            "asinh": asinh,
            "acosh": acosh,
            "atanh": atanh,
            "exp": exp,
            "expm1": expm1,
            "log": log,
            "log10": log10,
            "log2": log2,
            "pow": pow,
            "sqrt": sqrt,
            "ceil": ceil,
            "floor": floor,
            "trunc": trunc,
            "modf": __import__("math").modf,
            "frexp": frexp,
            "ldexp": ldexp,
            "fmod": fmod,
            "fabs": fabs,
            "copysign": copysign,
            "degrees": degrees,
            "radians": radians,
            "erf": erf,
            "erfc": erfc,
            "gamma": gamma,
            "lgamma": lgamma,
            "isfinite": isfinite,
            "isinf": isinf,
            "isnan": isnan,
            "e": e,
            "pi": pi,
            "ans": self.ans,
        }
        for item in self.storage.get_functions():
            name = item.get("name")
            variables = item.get("variables", [])
            expression = item.get("expression", "")
            if not name or expression is None:
                continue
            safe[name] = self._build_function(variables, expression, safe)
        return safe

    def _build_function(self, variables, expression, safe_globals):
        def generated(*args):
            if len(args) != len(variables):
                raise ValueError("wrong number of arguments")
            local_scope = {}
            for index, key in enumerate(variables):
                local_scope[key] = args[index]
            return eval(expression, safe_globals, local_scope)

        return generated

    def evaluate(self, expression):
        safe = self._safe_globals()
        result = eval(expression, safe)
        self.ans = result
        return result

