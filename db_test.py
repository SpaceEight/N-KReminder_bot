from dbProcess import save_remind, del_remind, connect_to_db

import unittest


class nk_bot(unittest.TestCase):

    def test_add(self):
        
        res = save_remind(716373936)
        self.assertEqual(res, (False, 'ERROR: File not found'))

    def test_remove(self):
        
        res = del_remind(1)
        self.assertEqual(res, True)


if __name__ == "__main__":
    unittest.main()

    