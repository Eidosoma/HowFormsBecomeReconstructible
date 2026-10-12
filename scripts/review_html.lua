-- Preserve substantive raw typesetting blocks as source instead of losing them.
function RawBlock(el)
  if el.format == 'tex' or el.format == 'latex' then
    if el.text:match('^%s*\\clearpage%s*$') then return {} end
    return pandoc.Div({pandoc.Para('Original typesetting block (LaTeX source):'), pandoc.CodeBlock(el.text, {class='latex'})})
  end
end
