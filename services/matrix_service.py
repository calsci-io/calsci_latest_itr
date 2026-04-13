class MatrixService:
    def parse(self, text):
        rows = []
        for raw_row in str(text).split(";"):
            raw_row = raw_row.strip()
            if not raw_row:
                continue
            row = []
            for raw_value in raw_row.split(","):
                row.append(float(raw_value.strip()))
            rows.append(row)
        if not rows:
            raise ValueError("empty matrix")
        width = len(rows[0])
        for row in rows:
            if len(row) != width:
                raise ValueError("ragged matrix")
        return rows

    def format(self, matrix):
        return ["[" + ", ".join(self._fmt(value) for value in row) + "]" for row in matrix]

    def add(self, a, b):
        self._require_same_shape(a, b)
        return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]

    def multiply(self, a, b):
        if len(a[0]) != len(b):
            raise ValueError("shape mismatch")
        out = []
        for i in range(len(a)):
            row = []
            for j in range(len(b[0])):
                total = 0.0
                for k in range(len(b)):
                    total += a[i][k] * b[k][j]
                row.append(total)
            out.append(row)
        return out

    def transpose(self, matrix):
        return [[matrix[i][j] for i in range(len(matrix))] for j in range(len(matrix[0]))]

    def determinant(self, matrix):
        self._require_square(matrix)
        size = len(matrix)
        if size == 1:
            return matrix[0][0]
        if size == 2:
            return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
        det = 0.0
        for col in range(size):
            minor = []
            for row in range(1, size):
                minor_row = []
                for inner_col in range(size):
                    if inner_col != col:
                        minor_row.append(matrix[row][inner_col])
                minor.append(minor_row)
            det += ((-1) ** col) * matrix[0][col] * self.determinant(minor)
        return det

    def inverse(self, matrix):
        self._require_square(matrix)
        size = len(matrix)
        augmented = []
        for row_index, row in enumerate(matrix):
            augmented.append(list(row) + [1.0 if row_index == col else 0.0 for col in range(size)])

        for pivot in range(size):
            pivot_row = pivot
            while pivot_row < size and abs(augmented[pivot_row][pivot]) < 1e-9:
                pivot_row += 1
            if pivot_row == size:
                raise ValueError("matrix is singular")
            if pivot_row != pivot:
                augmented[pivot], augmented[pivot_row] = augmented[pivot_row], augmented[pivot]

            pivot_value = augmented[pivot][pivot]
            for col in range(size * 2):
                augmented[pivot][col] /= pivot_value

            for row in range(size):
                if row == pivot:
                    continue
                factor = augmented[row][pivot]
                for col in range(size * 2):
                    augmented[row][col] -= factor * augmented[pivot][col]

        return [row[size:] for row in augmented]

    def rank(self, matrix):
        rows = [list(row) for row in matrix]
        row_count = len(rows)
        col_count = len(rows[0])
        rank = 0
        pivot_row = 0
        for pivot_col in range(col_count):
            best = pivot_row
            while best < row_count and abs(rows[best][pivot_col]) < 1e-9:
                best += 1
            if best == row_count:
                continue
            rows[pivot_row], rows[best] = rows[best], rows[pivot_row]
            pivot_value = rows[pivot_row][pivot_col]
            for col in range(pivot_col, col_count):
                rows[pivot_row][col] /= pivot_value
            for row in range(row_count):
                if row == pivot_row:
                    continue
                factor = rows[row][pivot_col]
                for col in range(pivot_col, col_count):
                    rows[row][col] -= factor * rows[pivot_row][col]
            rank += 1
            pivot_row += 1
            if pivot_row == row_count:
                break
        return rank

    def _require_square(self, matrix):
        if len(matrix) != len(matrix[0]):
            raise ValueError("matrix must be square")

    def _require_same_shape(self, a, b):
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            raise ValueError("shape mismatch")

    def _fmt(self, value):
        if int(value) == value:
            return str(int(value))
        return "%.5g" % value

