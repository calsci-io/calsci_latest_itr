# Scientific Calculator Apps

These apps implement **scientific and matrix‑based tools** used by the calculator. Most of them present a form to collect inputs and then render results on the display.

## Apps

- **`add_matrices.py`** – Add matrices.
- **`constants.py`** – Built‑in scientific constants lookup.
- **`determinant.py`** – Determinant calculator.
- **`eigen_values.py`** – Eigenvalue solver.
- **`graph.py`** – Graph plotting tool.
- **`lu_decomposition.py`** – LU decomposition.
- **`matrix_inverse.py`** – Matrix inverse solver.
- **`matrix_mul_2.py`** – Matrix multiplication.
- **`matrix_operations.py`** – Menu for matrix operations.
- **`mymolecule.py`** – Molecule‑related calculations (custom tool).
- **`qr_decomposition.py`** – QR decomposition.
- **`quad_eqn_sol.py`** – Quadratic equation solver.
- **`rank.py`** – Matrix rank.
- **`reduced_row_echelon.py`** – RREF solver.
- **`row_echelon_form.py`** – Row‑echelon form.
- **`simultanious_eqn_sol.py`** – Simultaneous equation solver.
- **`transpose.py`** – Matrix transpose.

## How to use

Open **Scientific Calculator** from the root menu and select a tool. Most screens:
- use the `form` buffer for inputs,
- update with `form.update_buffer(...)`,
- render via `form_refresh.refresh(state=nav.current_state())`.
