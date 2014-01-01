if exists("b:current_syntax")
  finish
endif

syn keyword pakeDirective       target set append configuration
syn keyword pakeTargetType      application static_library phony
syn keyword pakeArgument        sources link_with depends_on run_before run_after library_dirs include_dirs compiler_flags linker_flags artefacts prerequisites
syn keyword pakeArgument        application_suffix compiler export archiver resources visible_in
syn match pakeSpecialVariable   "__path"
syn match pakeSpecialVariable   "__build"
syn match pakeSpecialVariable   "__null"
syn match pakeSpecialVariable   "__default"
syn match pakeSpecialVariable   "__configuration"
syn match pakeSpecialVariable   "__name"
syn match pakeComment           "#.*$"
syn match pakeIdentifier1       "$[^ )]*" contains=pakeSpecialVariable
syn match pakeIdentifier2       "${[^ )]*}" contained contains=pakeSpecialVariable
syn region pakeString           start='"' end='"' contains=pakeIdentifier2

hi def link pakeDirective        Statement
hi def link pakeTargetType       Type
hi def link pakeArgument         Keyword
hi def link pakeSpecialVariable  Constant
hi def link pakeIdentifier1      Identifier
hi def link pakeIdentifier2      Identifier
hi def link pakeString           Constant
hi def link pakeComment          Comment

let b:current_syntax = "pake"
