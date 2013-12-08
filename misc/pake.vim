if exists("b:current_syntax")
  finish
endif

syn keyword Statement target set append
syn keyword Type application static_library phony
syn keyword Keyword sources link_with depends_on run_before run_after library_dirs include_dirs compiler_flags
syn match Identifier "$[^ )]*"
syn match Constant "__path"
syn match Comment "#.*$"

let b:current_syntax = "pake"
