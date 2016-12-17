#!/usr/bin/env python
"""
PyLuaTblParser.py
A Python Class Parser for Lua Table
Author: Zhongjun Wu
Email: wuzhongjun1992@126.com
"""
import sys, math
import string

# lua keywords that cannot be used as identifiers
lua_words = ("and", "break", "do", "else", "elseif", \
             "end", "false", "for", "function", "if", \
             "in", "local", "nil", "not", "or", \
             "repeat", "return", "then", "true", "until", \
             "while")

# valid chars for judging valid identifiers
valid_char = [chr(ord('A') + i) for i in range(0, 26)]
valid_char2 = [chr(ord('a') + i) for i in range(0, 26)]
valid_num = [chr(ord('0') + i) for i in range(0, 10)]
valid_char.extend(valid_char2)
valid_char.extend(valid_num)
valid_char.append('_')

valid_hex = [chr(ord('A') + i) for i in range(0, 6)]
valid_hex2 = [chr(ord('a') + i) for i in range(0, 6)]
valid_hex.extend(valid_hex2)
valid_hex.extend(valid_num)

hex_map = {'0':0, '1':1, '2':2, '3':3, '4':4, \
           '5':5, '6':6, '7':7, '8':8, '9':9, \
           'a':10, 'b':11, 'c':12, 'd':13, 'e':14, 'f':15, \
           'A':10, 'B':11, 'C':12, 'D':13, 'E':14, 'F':15}

# chars that should be escape in lua string
lua_escapes = {'a':'\a', 'b':'\b', 'f':'\f', 'n':'\n', 'r':'\r', \
               't':'\t', 'v':'\v', '\\':'\\', '"':'"', '\'':'\'', \
               '\n':'\n', 'x':'escape mode'}

class PyLuaTblParser(object):
    def __init__(self):
        '''
        dict initiate
        '''
        self.idx_ = 0
        self.in_str_ = ""
        self.dict_ = {}
        self.list_ = []
        self.data_str_ = {}

    def loadDict(self, d):
        '''
        Func: Load data from a dict
        Notice: Exclude key that is not num or string
        '''
        self.dict_ = {}
        self.list_ = []
        tmp_dict = {}
        for key, val in d.items():
            if isinstance(key, unicode):
                key = key.encode("ascii")
            if isinstance(key, int) or \
               isinstance(key, long) or \
               isinstance(key, float) or \
               isinstance(key, str):
                tmp_dict[key] = val
        s = self.recurDump(tmp_dict)
        self.load(s)

    def dumpDict(self):
        '''
        Func: Return a dict from self data
        '''
        # self.data_str_ = str(self.dict_)
        # return eval(self.data_str_)
        if len(self.dict_) != 0:
            self.data_str_ = str(self.dict_)
            return eval(self.data_str_)
        elif len(self.list_) != 0:
            tmp_dic = {}
            cnt = 1
            for x in self.list_:
                tmp_dic[cnt] = eval(str(x))
                cnt = cnt + 1
            return eval(str(tmp_dict))
        else:
            return {}

    def load(self, s):
        '''
        Func: Load Lua code from raw string
        '''
        self.dict_ = {}
        self.list_ = {}
        self.in_str_ = s
        self.parseStr()

    def dump(self):
        if len(self.dict_) != 0:
            s = self.recurDump(self.dict_)
        elif len(self.list_) != 0:
            s = self.recurDump(self.list_)
        else:
            s = '{}'
        return s

    def loadLuaTable(self, f):
        '''
        Func: Load Lua code from file
        '''
        raw_f = "%r"%(f)
        in_file = open(f, 'r')
        self.in_str_ = in_file.read()

        in_file.close()

        # self.printInStr(self.in_str_)
        self.parseStr()
    
    def dumpLuaTable(self, f):
        '''
        Func: Dump Lua code to file
        '''
        s = self.dump()
        raw_f = "%r"%(f)
        in_file = open(f, 'w')
        in_file.write(s)
        in_file.close()

    def parseStr(self):
        '''
        Func: Parse the inner string to create Python Dict
        '''
        # first: kick out the comments
        s1 = self.commentOutV2(self.in_str_)
        # second: parse all string to char @
        s2, str_list = self.stringParse(s1)
        # third: parse all (nil, boolean, number, identifiers) to char $
        s3, val_list = self.valParse(s2)
        # fourth: convert the @ and $ position to value
        pos_dict = self.createPosToVal(s3, str_list, val_list)
        ''' 
        print s1
        print s2
        print s3
        print pos_dict
        '''
        # fifth: recursively constructs dict
        self.tmp_struct_ = self.recurParse(s3, pos_dict, 0)
        if isinstance(self.tmp_struct_, list):
            self.list_ = self.tmp_struct_
        #    print self.list_
        elif isinstance(self.tmp_struct_, dict):
            self.dict_ = self.tmp_struct_
        #    print self.dict_

    def recurParse(self, s, pos_dict, offset=0):
        '''
        Func: Recursively construct inner data from simplified code
        '''
        cur_dict = {}
        cur_list = []
        bracket_stack = []
        idx = 0
        strcnt = len(s)
        start_idx = 0
        while idx < strcnt:
            cur = s[idx]
            if cur == '{':
                if len(bracket_stack) == 0:
                    start_idx = idx
                bracket_stack.append('{')
                idx = idx + 1
            elif cur == '}' and len(bracket_stack) != 1:
                bracket_stack.pop()
                if len(bracket_stack) == 0:
                    return self.dataReduce(cur_dict, cur_list)
                idx = idx + 1
            elif cur == ',' or cur == ';' or cur == '}':
                if len(bracket_stack) == 1:
                    sub_s = s[start_idx + 1 : idx] 
                  #  print "sub_s  :   %s     offset   :  %d"%(sub_s, offset)
                    if len(sub_s) == 0:
                        return self.dataReduce(cur_dict, cur_list)
                    elif sub_s[0] == '{': # {}
                        cur_list.append( \
                            self.recurParse(sub_s, pos_dict, start_idx + offset + 1))
                    elif sub_s[0] == '[': # []
                        keyval_key = pos_dict[start_idx + 2 + offset]
                        if sub_s[4] == '{': # [@]={}
                            val_sub_s = sub_s[4 : ]
                            keyval_val = \
                                self.recurParse(val_sub_s, pos_dict, \
                                    start_idx + offset + 5)
                        else: # [@]=@
                            keyval_val = pos_dict[start_idx + 5 + offset]
                        cur_dict[keyval_key] = keyval_val
                    elif '=' in sub_s: # @=@ or @={}
                        keyval_key = pos_dict[start_idx + 1 + offset]
                        if sub_s[2] == '{': # @={}
                            val_sub_s = sub_s[2 : ]
                            keyval_val = \
                                self.recurParse(val_sub_s, \
                                    pos_dict, start_idx + 3 + offset)
                        else: # @=@
                            keyval_val = pos_dict[start_idx + 3 + offset]
                        cur_dict[keyval_key] = keyval_val
                    else: # @    
                        cur_list.append(pos_dict[start_idx + 1 + offset])
                    
                    start_idx = idx
                  #  print "start_idx = %d" % (start_idx)
                    idx = idx + 1
                else:
                    idx = idx + 1
                if cur == '}':
                    return self.dataReduce(cur_dict, cur_list)
            else:
                idx = idx + 1
        return {}
                    
    def dataReduce(self, cur_dict, cur_list):
        '''
        Func: to decide a structure to be a list or a dict
        '''
        if cur_dict:  
            # pop key in cur_dict which value is none
            for keys, vals in cur_dict.items():
                if isinstance(vals, type(None)):
                    cur_dict.pop(keys)
            if cur_dict:  # check again
                # pop key in cur_dict which exists in list
                for i in range(0, len(cur_list)):
                    if cur_dict.has_key(i + 1):
                        cur_dict.pop(i + 1)
                if cur_dict:  # decide to be a dict
                    for i in range(0, len(cur_list)):
                        # update dict data with list data
                        cur_dict[i + 1] = cur_list[i]
                        # filter value that is None
                        if isinstance(cur_dict[i + 1], type(None)):
                           cur_dict.pop(i + 1) 
                    cur_list = []  # clear list data
                    return cur_dict
                else:  # decide to be a list
                    return cur_list  # dict is already empty
            else:  # decide to be a list
                return cur_list
        else:
            return cur_list
      #  return (cur_dict, cur_list)

    def recurDump(self, cur_item):
        if isinstance(cur_item, type(None)):
            return "nil"
        elif isinstance(cur_item, float) or \
             isinstance(cur_item, long) or \
             isinstance(cur_item, int):
            return str(cur_item)
        elif isinstance(cur_item, bool):
            if cur_item == False:
                return "false"
            else:
                return "true"
        elif isinstance(cur_item, unicode):
            cur_item = cur_item.encode("ascii")
            return repr(cur_item)
        elif isinstance(cur_item, str):
            return repr(cur_item)
        elif isinstance(cur_item, list):
            res_str = '{'
            if len(cur_item) != 0:
                for x in cur_item:
                    res_str = res_str + self.recurDump(x) + ','
            res_str = res_str + "}"
            return res_str
        elif isinstance(cur_item, dict):
            res_str = '{'
            if len(cur_item) != 0:
                for keys, vals in cur_item.items():
                    res_str = res_str + '[' + self.recurDump(keys) +\
                              ']=' + self.recurDump(vals) + ','
            res_str = res_str + "}"
            return res_str        
            

    def readStrSingle(self, s, str_seq, idx):
        '''
        Func: Try to read a string starts with ' or "
        '''
        start_idx = idx
        strcnt = len(s)
        state = "normal"
        while idx < strcnt:
            cur = s[idx]
            if state == "normal":
                if cur == '\\':  # enter escape mode
                    state = "escape"
                # line has been switched when reading string
                elif cur == '\n':  
                    raise Exception, "Read String Error: Line has been Switched"
                elif cur == str_seq:
                    converted_str = self.getCorrespondStr(s[start_idx : idx])
                    # return the converted string and end idx
                    idx = idx + 1
                    return (converted_str, idx)
            elif state == "escape":
                # check char that can be escape 
                if cur not in lua_escapes and cur not in valid_num:
                    raise Exception, "Read String Error: Invalid Escape"
                else:
                    state = "normal"
            idx = idx + 1
        raise Exception, \
            "Read String Error: Cannot finish till text end\nidx = %d\n%s" % \
            (idx, s)
    
    def readStrMulti(self, s, match_str, idx):
        '''
        Func: Try to read a multiline string with [[ or [==[ (raw string)
        '''
        start_idx = idx
        strcnt = len(s)
        while idx < strcnt:
            cur = s[idx]
            if cur == ']':
                if idx + len(match_str) - 1 < strcnt:
                    if s[idx : idx + len(match_str)] == match_str:
                        idx = idx + len(match_str)
                        # delete the start \n
                        if s[start_idx] == '\n':
                            return (s[start_idx + 1: idx - len(match_str)], idx)
                        else:
                            return (s[start_idx: idx - len(match_str)], idx)
                    else:
                        idx = idx + 1
                else:
                    raise Exception, \
                          "multiline string definition without right part"
            else:
                idx = idx + 1      
        raise Exception, "Read String Error: Cannot finish till text end"

    def getCorrespondStr(self, s):
        res_str = ''
        idx = 0
        state = "normal"
        strcnt = len(s)
        while idx < strcnt:  # greedy convert code string to real string
            cur = s[idx]
            if state == "normal":
                if cur == '\\':
                    idx = idx + 1
                    nxt = s[idx]
                    if nxt != 'x' and nxt not in valid_num:
                        res_str = res_str + lua_escapes[nxt]
                        idx = idx + 1
                    elif nxt in valid_num: # 3bits greedy convert
                        escape_num = 0
                        for i in range(0, 3):
                            if idx + i < strcnt and s[idx + i] in valid_num:
                                escape_num = escape_num * 10 + \
                                             ord(s[idx + i]) - 48
                            else:
                                break
                        if escape_num > 255:
                            raise Exception, \
                                  "Convert String Error: Three bits num too large"
                        else:
                            res_str = res_str + chr(escape_num)
                            idx = idx + i + 1
                    elif nxt == 'x': # 2hexbits convert
                        if idx + 2 < strcnt and s[idx + 1] in valid_hex \
                                            and s[idx + 2] in valid_hex:
                            res_str = res_str + \
                                chr(hex_map[s[idx + 1]] * 16 + hex_map[s[idx + 2]])
                            idx = idx + 3
                        else:
                            raise Exception, \
                                  "Convert String Error: Two hex bits convert fail"
                else:
                    res_str = res_str + s[idx]
                    idx = idx + 1
                
        return res_str

    def stringParse(self, tmp_str):
        '''
        Func: parse all string to char @ in the lua code 
        '''
        idx = 0
        s = tmp_str
        str_list = []
        while idx < len(s):
            cur = s[idx]
            strcnt = len(s)
            if cur == '[':
                if idx + 1 < strcnt and s[idx: idx + 2] == "[[":
                    match_str = "]]"
                    start_idx = idx 
                    idx = idx + 2
                    (converted_str, end_idx) = self.readStrMulti(s, match_str, idx)
                    str_list.append(converted_str)
                    s = s[0 : start_idx] + '@' + s[end_idx : ]
                    idx = start_idx + 1
                elif idx + 1 < strcnt and s[idx + 1] == '=':
                    m_idx = idx + 1
                    while m_idx < strcnt and s[m_idx] == '=':
                        m_idx = m_idx + 1
                    match_str = s[idx: m_idx + 1].replace('[', ']')
                    start_idx = idx
                    idx = m_idx + 1
                    (converted_str, end_idx) = self.readStrMulti(s, match_str, idx)
                    str_list.append(converted_str)
                    s = s[0 : start_idx] + '@' + s[end_idx : ]
                    idx = start_idx + 1
                else:
                    idx = idx + 1
            elif cur == '\'' or cur == '\"':
                start_idx = idx
                idx = idx + 1
                (converted_str, end_idx) = self.readStrSingle(s, cur, idx)
                str_list.append(converted_str)
                s = s[0 : start_idx] + '@' + s[end_idx : ]
                idx = start_idx + 1
            else:
                idx = idx + 1
        return \
            s.replace('\n', '').replace(' ', '').replace('\t', '').replace('\r', ''),\
                str_list
    
    def valParse(self, tmp_str):
        '''
        Func: parse all nil, boolean, number to $ in the lua code
        '''
        idx = 0
        s = tmp_str
        val_list = []
        while idx < len(s):
            cur = s[idx]
            # identifiers begin
            if cur.isalpha() or cur == '_':
                start_idx = idx 
                while s[idx] in valid_char:
                    idx = idx + 1
                val_name = s[start_idx : idx]
                if val_name == "nil":
                    val_list.append(None)
                elif val_name == "true" or val_name == "True":
                    val_list.append(True)
                elif val_name == "false" or val_name == "False":
                    val_list.append(False)
                else:
                    val_list.append(val_name)
                s = s[0 : start_idx] + '$' + s[idx : ]
                idx = start_idx + 1
            elif cur not in ['{', '}', '[', ']', '=', ',' , ';', '@']:
                start_idx = idx
                while s[idx] not in ['{', '}', '[', ']', '=', ',' , ';', '@']:
                    idx = idx + 1
                val_name = s[start_idx : idx]
                if '0x' in val_name or '0X' in val_name:
                    val = float.fromhex(val_name)
                else:
                    val = eval(val_name)
                val_list.append(val)
                s = s[0 : start_idx] + '$' + s[idx : ]
                idx = start_idx + 1
            else:
                idx = idx + 1

        return s, val_list

    def createPosToVal(self, s, str_list, val_list):
        '''
        Func: convert the @ and $ position to value
        '''
        idx = 0
        strcnt = len(s)
        str_idx = 0
        val_idx = 0
        pos_dict = {}
        while idx < strcnt:
            cur = s[idx]
            if cur == '@':
                pos_dict[idx] = str_list[str_idx]
                str_idx = str_idx + 1
            elif cur == '$':
                pos_dict[idx] = val_list[val_idx]
                val_idx = val_idx + 1
            idx = idx + 1
        return pos_dict

    def commentOutV2(self, tmp_str):
        '''
        Func: commentOutV2 add multiline string defined by [[ or [--[
        '''
        idx = 0
        state = "normal"
        # tmp_str = self.in_str_
        res_str = ""
        strcnt = len(tmp_str)
        match_str = ""
        tt = 0
        while idx < strcnt:
            cur = tmp_str[idx]
            if state == "normal":
                if cur == '-':
                    if idx + 3 < strcnt and tmp_str[idx : idx + 4] == "--[[":
                        state = "multi_comment"
                        idx = idx + 4
                    elif idx + 1 < strcnt and tmp_str[idx : idx + 2] == "--":
                        state = "single_comment"
                        idx = idx + 2
                    # TODO: deal with number that less than zero
                    else:
                    #    raise Exception, "-- single line comment error"
                        res_str = res_str + cur
                        idx = idx + 1
                elif cur == '\'':
                  #  print "string1 begin idx = %d" % (idx)
                  #  tt = idx 
                    state = "string1"
                    res_str = res_str + cur
                    idx = idx + 1
                elif cur == '\"':
                  #  print "string2 begin idx = %d" % (idx)
                  #  tt = idx 
                    state = "string2"
                    res_str = res_str + cur
                    idx = idx + 1
                elif cur == '[':
                    if idx + 1 < strcnt and tmp_str[idx : idx + 2] == "[[":
                        state = "multi_string"
                        match_str = "]]"
                        res_str = res_str + tmp_str[idx : idx + 2]
                        idx = idx + 2
                    elif idx + 1 < strcnt and tmp_str[idx + 1] == '=':
                        m_idx = idx + 1
                        while m_idx < strcnt and tmp_str[m_idx] == '=': 
                            m_idx = m_idx + 1
                        if m_idx >= strcnt:
                            raise Exception, "multiline string definition error"
                        else:
                            if tmp_str[m_idx] != '[':
                                raise Exception, "multiline string definition error"
                            else:
                                state = "multi_string"
                                match_str = tmp_str[idx : m_idx + 1].replace('[', ']')
                                res_str = res_str + tmp_str[idx : m_idx + 1]
                                idx = m_idx + 1
                    else:
                        res_str = res_str + cur
                        idx = idx + 1
                else:
                    res_str = res_str + cur
                    idx = idx + 1
            elif state == "single_comment":
                if cur == '\n':
                    res_str = res_str + cur
                    state = "normal"
                else: 
                    pass
                idx = idx + 1
            elif state == "multi_comment":
                if cur == ']':
                    if idx + 1 < strcnt:
                        if tmp_str[idx : idx + 2] == "]]":
                            state = "normal"
                            idx = idx + 2
                        else:
                            idx = idx + 1
                    else:
                        raise Exception, "multiline comment without right part"
                else:
                    idx = idx + 1
            elif state == "string1" or state == "string1_escape":
                if state == "string1":
                    if cur == '\\':
                        state = "string1_escape"
                    elif cur == '\n':
                        raise Exception, "Read String Error: Line has been switched"
                    elif cur == '\'':
                      #  print tmp_str[tt : idx + 1]
                      #  print "string1 end idx = %d" % (idx) 
                        state = "normal"
                    res_str = res_str + cur
                    idx = idx + 1
                elif state == "string1_escape":
                    if cur not in lua_escapes and cur not in valid_num:
                        raise Exception, "Read String Error: Invalid Escape"
                    else:
                        state = "string1"
                    res_str = res_str + cur
                    idx = idx + 1
            elif state == "string2" or state == "string2_escape":
                if state == "string2":
                    if cur == '\\':
                        state = "string2_escape"
                    elif cur == '\n':
                        raise Exception, "Read String Error: Line has been switched"
                    elif cur == '\"':
                      #  print tmp_str[tt : idx + 1]
                      #  print "string2 end idx = %d" % (idx) 
                        state = "normal"
                    res_str = res_str + cur
                    idx = idx + 1
                elif state == "string2_escape":
                    if cur not in lua_escapes and cur not in valid_num:
                        raise Exception, "Read String Error: Invalid Escape"
                    else:
                        state = "string2"
                    res_str = res_str + cur
                    idx = idx + 1
            elif state == "multi_string":
                if cur == ']':
                    if idx + len(match_str) - 1 < strcnt:
                        if tmp_str[idx : idx + len(match_str)] == match_str:
                            state = "normal"
                            res_str = res_str + match_str
                            idx = idx + len(match_str)
                        else:
                            res_str = res_str + cur
                            idx = idx + 1
                    else:
                        raise Exception, \
                              "multiline string definition without right part"
                else:
                    res_str = res_str + cur
                    idx = idx + 1

        if state != "single_comment" and state != "normal":
            raise Exception, "comment out error, last state: %s not end"%(state)
        return res_str 

    def printInStr(self, s):
        if s != "":
            print "-------------------str--------------------"
            print "%s"%(s)
            print "-------------------repr-------------------"
            print repr(s)

def main():
    a1 = PyLuaTblParser()
    a2 = PyLuaTblParser()
    a3 = PyLuaTblParser()

    str_d0 = '''{ 
     'array': [65, 23, 5], 
     'dict': { 
          'mixed': {
               1: 43,
               2: 54.33,
               3: False,
               4: 9,
               'string': 'value'
          },
          'array': [3, 6, 4],
          'string': 'value'
        }
    } '''
    d = {u"rrr":"a",2:"b",3:"c"}
    test_str = '{array = {65,23,5,},dict = {mixed = {43,54.33,false,9,string = "value",},array = {3,6,4,},string = "value",},}' 
    a1.loadLuaTable('test.lua')
    print a1.dump()
    a1.dumpLuaTable('result.lua')
    d1 = a1.dumpDict()
    print d1
    print test_str
    a1.load(test_str)
    print a1.dumpDict()
    a1.loadDict(d)
    print a1.dumpDict()
if __name__ == "__main__":
    main()

