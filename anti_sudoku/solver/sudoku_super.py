'''
Date: 2022-10-26 15:09:29
LastEditors: yuhhong
LastEditTime: 2022-10-28 14:32:37
'''
import sys
sys.setrecursionlimit(15000)

class Sudoku: 

    def __init__(self, path=None):
        self.board = []
        self.blank_idx = []
        self.sq_len = 9
        self.sub_sq_len = 3
        
        if path: # read the board from a file
            print('Init the Sudoku board from the file: {}'.format(path))
            with open(path, 'r') as f:
                data = f.readlines()
            for row in data:
                self.board += row.split()
            
            self.blank_idx = [i for i, item in enumerate(self.board) if item == '-']

        else: # generate a new board
            print('Init the Sudoku board by generating')
            raise Exception('Not implement yet!')

        if len(self.board) == 0: # make sure the board is not empty
            raise ValueError('Empty board!')
        
        # used in constraint propagation
        self.potential_values = self._init_potential_values(self.board)
        self.arcs = self._init_arcs(self.blank_idx)
        self.agendas = self.arcs.copy() # attention the difference between deep copy and shallow copy

        # used in backtracking
        self.track_indexes = {k:-1 for k in self.blank_idx}
        
    # -------------------------------------
    # External functions
    # -------------------------------------

    def show_board(self):
        list_board = []
        for item in self.board:
            list_board.append(str(item))
        print('>>>')
        for i in range(self.sq_len):
            print('|{}|'.format(','.join(list_board[int(i*self.sq_len): int((i+1)*self.sq_len)])))
        # print('blank indexes: {}'.format(self.blank_idx))
        print('>>>')

    def solve(self):
        print('Solving the Sudoku...')

        # constraint propagation
        # Note: Sometimes the potential values are not unique after constraint 
        # propagation, and backtracking is still needed. 
        i = 0
        agenda_len = len(self.agendas)
        while i < agenda_len: 
            changed_indexes = self._modify_potential_values(self.agendas[i])
            
            if len(changed_indexes) > 0: # update agenda
                for idx in changed_indexes: 
                    related_arc = [arc for arc in self.arcs if arc[0] == idx]
                    self.agendas = self.agendas + related_arc
                    agenda_len += len(related_arc)
                    # print('Add {} arcs'.format(len(related_arc)))
            i += 1
        print('All potential values for empty positions:\n', self.potential_values)

        # backtracking
        print('Let\'s get one possible solution...')
        self.board = self._fill_board(self.board, 0)
        print('Done!')

    # -------------------------------------
    # Internal functions: Init
    # -------------------------------------
    
    def _init_potential_values(self, board): 
        values = {}
        # init the potential values
        for i in self.blank_idx:
            values[i] = set([*range(1, self.sq_len+1)])

        # look in row, column, and block
        for i in range(self.sq_len):
            for indexes in [self._row_indexes(i), self._col_indexes(i), self._block_indexes(i)]: 
                item_list = [int(board[idx]) for idx in indexes if board[idx] != '-']
                item_set = set(item_list)
                # remove exsist values in potential values
                for k, v in values.items():
                    if k in indexes: 
                        values[k] = v - item_set

        # convert potential values' set to list
        for k, v in values.items(): 
            values[k] = list(v)
        return values

    def _init_arcs(self, blank_idx):
        arcs = []
        # split blank indexes by row, column, and block
        for i in range(self.sq_len): 
            blank_in_row = [idx for idx in self._row_indexes(i) if idx in blank_idx] 
            for idx in blank_in_row: 
                arcs.append((idx, 'row', [jdx for jdx in blank_in_row if jdx != idx]))

            blank_in_col = [idx for idx in self._col_indexes(i) if idx in blank_idx] 
            for idx in blank_in_col: 
                arcs.append((idx, 'col', [jdx for jdx in blank_in_col if jdx != idx]))

            blank_in_block = [idx for idx in self._block_indexes(i) if idx in blank_idx] 
            for idx in blank_in_block: 
                arcs.append((idx, 'block', [jdx for jdx in blank_in_block if jdx != idx]))
        return arcs

    # -------------------------------------
    # Internal functions: constraint propagation
    # -------------------------------------

    def _modify_potential_values(self, agenda): 
        # print('working on: ', agenda, self.potential_values[agenda[0]])
        idx = agenda[0]
        check_type = agenda[1]
        related_idx = agenda[2]

        new_potential_values = []
        for v in self.potential_values[idx]:
            # check whether there is a solution when board[idx] == v
            new_board = self.board.copy()
            new_board[idx] = v
            
            if self._fill_related_indexes(new_board, check_type, related_idx, 0, track={k:-1 for k in related_idx}): 
                new_potential_values.append(v)

        # if there is only one potential value, it can be fixed
        if len(new_potential_values) == 1:
            self.board[idx] = new_potential_values[0]
            self.blank_idx = [jdx for jdx in self.blank_idx if jdx != idx]
            # print('Fix {} as {}'.format(idx, self.board[idx]))
            # print('# Blank indexes:', len(self.blank_idx))

        # if potential values of idx are updated, the agenda need to be updated too
        if new_potential_values != self.potential_values[idx]:
            # print('Change ->', self.potential_values[idx], new_potential_values)
            self.potential_values[idx] = new_potential_values
            return related_idx
        else:
            # print('No Change\n')
            return []

    def _fill_related_indexes(self, board, check_type, related_idx, i, track): 
        if i < 0:
            # print('remove potential values\n')
            return False
        elif i == len(related_idx): 
            # print('keep potential values\n')
            return True
        
        pos = related_idx[i]
        if track[pos] < len(self.potential_values[pos]) - 1:
            track[pos] += 1
            board[pos] = self.potential_values[pos][track[pos]]
        else: 
            track[pos] = -1
            board[pos] = '-'
            # print('try all possible values of {}, but failure, track back to {}'.format(pos, i-1))
            return self._fill_related_indexes(board, check_type, related_idx, i-1, track)

        # check validation
        val = self._check_board(board, check_type)
        if val:
            # print('success fill ({}, {}, {}), next blank index'.format(i, pos, board[pos]))
            return self._fill_related_indexes(board, check_type, related_idx, i+1, track)
        else:
            # print('failure fill ({}, {}, {}), try another potential value'.format(i, pos, board[pos]))
            return self._fill_related_indexes(board, check_type, related_idx, i, track)

    # -------------------------------------
    # Internal functions: backtracking
    # -------------------------------------

    def _fill_board(self, board, i): 
        if i == len(self.blank_idx): # complete!
            return board
        pos = self.blank_idx[i]

        # print(pos, board[pos], self.track_indexes[pos], self.potential_values[pos])
        if board[pos] == '-' or self.track_indexes[pos] < len(self.potential_values[pos]) - 1: 
            self.track_indexes[pos] += 1
            board[pos] = self.potential_values[pos][self.track_indexes[pos]]
        else: 
            self.track_indexes[pos] = -1
            board[pos] = '-'
            return self._fill_board(board, i-1)

        # check validation
        val = self._check_board(board)
        if val:
            return self._fill_board(board, i+1)
        else:
            return self._fill_board(board, i)

    # -------------------------------------
    # Internal functions: utils
    # -------------------------------------

    def _check_board(self, board, check_type=None): 
        if check_type == 'row':
            for i in range(self.sq_len): 
                item_list = [int(board[idx]) for idx in self._row_indexes(i) if board[idx] != '-']
                item_set = set(item_list)
                if len(item_set) != len(item_list):
                    # print('ROW({}): {}, {}'.format(indexes, item_list, item_set))
                    return False
        elif check_type == 'col':
            for i in range(self.sq_len): 
                item_list = [int(board[idx]) for idx in self._col_indexes(i) if board[idx] != '-']
                item_set = set(item_list)
                if len(item_set) != len(item_list):
                    # print('COL({}): {}, {}'.format(indexes, item_list, item_set))
                    return False
        elif check_type == 'block': 
            for i in range(self.sq_len):  
                item_list = [int(board[idx]) for idx in self._block_indexes(i) if board[idx] != '-']
                item_set = set(item_list)
                if len(item_set) != len(item_list):
                    # print('BLOCK({}): {}, {}'.format(indexes, item_list, item_set))
                    return False
        else: # check row, column, and block
            for i in range(self.sq_len):
                for indexes in [self._row_indexes(i), self._col_indexes(i), self._block_indexes(i)]: 
                    item_list = [int(board[idx]) for idx in indexes if board[idx] != '-']
                    item_set = set(item_list)
                    if len(item_set) != len(item_list):
                        # print('ROW/COL/BLOCK({}): {}, {}'.format(indexes, item_list, item_set))
                        return False
        return True

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