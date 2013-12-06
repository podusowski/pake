if exists("b:current_syntax")
  finish
endif

syn keyword Statement target set append
syn keyword Type application static_library phony
syn keyword Keyword sources link_with depends_on run_before run_after
syn match Identifier "$[^ )]*"
"syn match Constant "$root_dir"
syn match Comment "#.*$"

let b:current_syntax = "pake"
