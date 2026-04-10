'''
Date: 2022-10-26 15:09:29
LastEditors: yuhhong
LastEditTime: 2022-10-28 14:32:37
'''
import sys
import copy
from itertools import combinations
sys.setrecursionlimit(15000)



class Sudoku: 

	def __init__(self, path=None):
		self.board = []
		self.blank_idx = []
		self.potential_values = {}
		self.visited_naked_cells = []
		self.sq_len = 9
		self.sub_sq_len = 3
		
		if path: # read the board from a file
			print('Init the Sudoku board from the file: {}'.format(path))
			with open(path, 'r') as f:
				data = f.readlines()
			for row in data:
				self.board += row.split()
			
			self.blank_idx = [i for i, item in enumerate(self.board) if item == '-']
			self.potential_values = {i: [] for i in self.blank_idx}

		else: # generate a new board
			print('Init the Sudoku board by generating')
			raise Exception('Not implement yet!')

		if len(self.board) == 0: # make sure the board is not empty
			raise ValueError('Empty board!')


	
	# -------------------------------------
	# External functions
	# -------------------------------------
	def show_board(self): 
		list_board = []
		for item in self.board:
			list_board.append(str(item))
		
		for i in range(self.sq_len):
			print('|{}|'.format(','.join(list_board[int(i*self.sq_len): int((i+1)*self.sq_len)])))
		# print('blank indexes: {}'.format(self.blank_idx))
		print('# empty cells: {}'.format(len(self.blank_idx)))
		
	def solve(self): 
		self.init_potential_values() # init self.potential_values
		
		cnt = 0
		while len(self.blank_idx) > 0: 
			print('\nIteration: {}'.format(cnt))
			# check naked cells
			# https://www.learn-sudoku.com/naked-pairs.html
			# https://www.learn-sudoku.com/naked-triplets.html
			for i in range(self.sq_len):  # group index
				self.check_naked_cells(self._block_indexes(i))
				self.check_naked_cells(self._row_indexes(i))
				self.check_naked_cells(self._col_indexes(i))
	
			# fill the cell if there is only one potential value for a cell
			# https://www.learn-sudoku.com/lone-singles.html
			current_potential_values = copy.deepcopy(self.potential_values)
			for k, v in current_potential_values.items(): 
				if len(v) == 1: 
					self._fill_cell(k, v[0], 'alone single')

			# fill the cell if there is only one possible position for a value in the group
			# https://www.learn-sudoku.com/hidden-singles.html
			for i in range(self.sq_len):
				self.check_hidden_singles(self._block_indexes(i))
				self.check_hidden_singles(self._row_indexes(i))
				self.check_hidden_singles(self._col_indexes(i))

			# check if pairs "only" appear in the same row, column, or block
			# https://www.learn-sudoku.com/hidden-pairs.html
			# https://www.learn-sudoku.com/hidden-triplets.html
			for i in range(self.sq_len):  # group index
				self.check_hidden_combo(self._block_indexes(i))
				self.check_hidden_combo(self._row_indexes(i))
				self.check_hidden_combo(self._col_indexes(i))

			# [overlap] eliminate potential values based on existing numbers in the same group
			# https://www.learn-sudoku.com/visual-elimination.html
			# self._visual_elimination()

			# https://www.learn-sudoku.com/omission.html
			self.omission()

			self.show_board()
			print('Potential values: {}'.format(self.potential_values))
			cnt += 1
			if cnt > 5: 
				print('Exceed the maximum number of iterations!')
				break

	# -------------------------------------
	# Internal functions: init
	# -------------------------------------
	def init_potential_values(self): 
		board = copy.deepcopy(self.board)

		values = {}
		# initialize potential values for each blank cell as all possible values
		for i in self.blank_idx: 
			row_i, col_i, block_i = self._index2coord(i)
			
			val = set(range(1, self.sq_len + 1))
			# eliminate potential values based on existing numbers in the same group
			# https://www.learn-sudoku.com/visual-elimination.html
			for related_i in self._row_indexes(row_i): 
				if related_i != i and related_i not in self.blank_idx: 
					val.discard(int(board[related_i]))

			for related_i in self._col_indexes(col_i):
				if related_i != i and related_i not in self.blank_idx: 
					val.discard(int(board[related_i]))

			for related_i in self._block_indexes(block_i):
				if related_i != i and related_i not in self.blank_idx: 
					val.discard(int(board[related_i]))
			values[i] = list(val)

		self.potential_values = values
		print('[LOG] Init potential values:\n{}'.format(self.potential_values))
	

	# -------------------------------------
	# Internal functions: basic techniques
	# -------------------------------------
	def omission(self):
		for num in range(1, 10):
			for block_i in range(9):
				block_cells = self._block_indexes(block_i)
				block_cells = [idx for idx in block_cells if idx in self.blank_idx] # do not consider filled cells
				possible_positions = [i for i in block_cells if num in self.potential_values[i]]

				# check if the number is confined to a single row or column within the block
				if len(possible_positions) > 1:
					row_confined = all(self._index2coord(pos)[0] == self._index2coord(possible_positions[0])[0] for pos in possible_positions)
					col_confined = all(self._index2coord(pos)[1] == self._index2coord(possible_positions[0])[1] for pos in possible_positions)

					if row_confined:
						row_i = self._index2coord(possible_positions[0])[0]
						for cell in self._row_indexes(row_i):
							if cell in self.blank_idx and cell not in block_cells and num in self.potential_values[cell]:
								self.potential_values[cell].remove(num)
								print(f"[LOG] Removed {num} from cell {cell} based on omission in row {row_i} and block {block_i}.")

					if col_confined:
						col_i = self._index2coord(possible_positions[0])[1]
						for cell in self._col_indexes(col_i):
							if cell in self.blank_idx and cell not in block_cells and num in self.potential_values[cell]:
								self.potential_values[cell].remove(num)
								print(f"[LOG] Removed {num} from cell {cell} based on omission in column {col_i} and block {block_i}.")

		print("[LOG] Omission complete.")

	def check_hidden_combo(self, indexes):
		possible_positions = self._update_potential_positions(indexes)

		for n in range(2, 5):  # handles pairs, triples, and quads
			for combo in combinations(possible_positions.keys(), n):
				positions = [possible_positions[v] for v in combo]
				flattened_positions = [p for sublist in positions for p in sublist]
				
				# check if all positions are identical and the number of positions matches n
				if len(set(map(tuple, positions))) == 1 and len(flattened_positions) == n:
					print(f'[LOG] Found hidden combo: {", ".join(map(str, combo))} in {positions[0]}')

					# convert the hidden set to a naked set
					for p in positions[0]:
						self.potential_values[p] = list(combo)

	def check_hidden_singles(self, indexes):
		possible_positions = self._update_potential_positions(indexes)
		
		for n, idx_list in possible_positions.items(): 
			if len(idx_list) == 1 and idx_list[0] in self.blank_idx: 
				self._fill_cell(idx_list[0], n, 'hidden single')
				possible_positions = self._update_potential_positions(indexes)

	def _update_potential_positions(self, indexes): 
		indexes = [idx for idx in indexes if idx in self.blank_idx] # do not consider filled cells
		possible_positions = {}

		for idx in indexes: 
			for value in self.potential_values[idx]: 
				if value in possible_positions.keys(): 
					possible_positions[value].append(idx)
				else: 
					possible_positions[value] = [idx]
		return possible_positions

	def check_naked_cells(self, indexes):
		indexes = [idx for idx in indexes if idx in self.blank_idx]

		for n in range(2, 5):
			for combo in combinations(indexes, n):
				values = [self.potential_values[p] for p in combo]
				if len(set(map(len, values))) == 1 and len(values[0]) == n and len(set(map(tuple, values))) == 1 and combo not in self.visited_naked_cells:
					self.visited_naked_cells.append(combo)
					print(f'[LOG] Found naked {n}: {", ".join(map(str, combo))}, {values[0]}')

					self._remove_related_potential_values(idxs=combo, values=values[0])

	# def _visual_elimination(self): 
	# 	for i in self.blank_idx: 
	# 		for related_i in set(self._related_indexes(i)): 
	# 			if related_i != i and related_i not in self.blank_idx:
	# 				related_v = int(self.board[related_i])
	# 				if related_v in self.potential_values[i]:
	# 					self.potential_values[i].remove(related_v)
	# 	print(f'[LOG] Visual elimination: {self.potential_values}')

	# -------------------------------------
	# Internal functions: utils
	# -------------------------------------
	def _fill_cell(self, idx, value, reason=None): 
		row_i, col_i, block_i = self._index2coord(idx)
		print('[LOG] Fill cell {} (r {}, c {}, b {}) with value {} ({})'.format(idx, row_i, col_i, block_i, value, reason))
		self.board[idx] = value
		self.blank_idx.remove(idx)
		self.potential_values.pop(idx)
		self._remove_related_potential_values(idxs=[idx], values=[value]) 

	def _remove_related_potential_values(self, idxs, values): 
		# idxs: index of the cell(s)
		# values: list of potential values to be removed

		related_indexes = set()
		if len(idxs) == 1: 
			related_indexes.update(set(self._related_indexes(idxs[0])))
		else:
			coords = [self._index2coord(idx) for idx in idxs]
			
			if all(c[0] == coords[0][0] for c in coords):
				related_indexes.update(set(self._row_indexes(coords[0][0])))
			if all(c[1] == coords[0][1] for c in coords):
				related_indexes.update(set(self._col_indexes(coords[0][1])))
			if all(c[2] == coords[0][2] for c in coords):
				related_indexes.update(set(self._block_indexes(coords[0][2])))

		related_indexes -= set(idxs)  # Exclude idxs from related_indexes
		related_indexes &= set(self.blank_idx)  # Only keep blank indexes

		for related_i in related_indexes:
			self.potential_values[related_i] = [
				v for v in self.potential_values[related_i] if v not in values
			]
			tmp_i, tmp_j, tmp_k = self._index2coord(related_i)
			print(f'[LOG] Remove potential values of {related_i} (r {tmp_i}, c {tmp_j}, b {tmp_k}) -> {self.potential_values[related_i]}')



	# -------------------------------------
	# Internal functions: Indexes
	# -------------------------------------
	def _row_indexes(self, i):
		return [int(i*self.sq_len+j) for j in range(self.sq_len)]

	def _col_indexes(self, i):
		return [int(j*self.sq_len+i) for j in range(self.sq_len)]

	def _block_indexes(self, i):
		idx_list = []
		for j in range(self.sub_sq_len): 
			start_idx = (i // self.sub_sq_len) * self.sq_len * self.sub_sq_len + (i % self.sub_sq_len) * self.sub_sq_len + j * self.sq_len
			idx_list += [*range(start_idx,start_idx+self.sub_sq_len)]
		return idx_list

	def _index2coord(self, i):
		row_i = i // self.sq_len
		col_i = i % self.sq_len
		block_i = row_i // self.sub_sq_len * self.sub_sq_len + col_i // self.sub_sq_len
		return (row_i, col_i, block_i)

	def _related_indexes(self, i):
		row_i, col_i, block_i = self._index2coord(i)
		return self._row_indexes(row_i) + self._col_indexes(col_i) + self._block_indexes(block_i)