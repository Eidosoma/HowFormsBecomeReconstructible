"""Inspect the frozen source API as syntax; never execute its scientific code."""
import ast
import support as s


def inspect_tree(text):
    tree=ast.parse(text)
    s.require(all(isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.Expr)) for node in tree.body),'No mutable source repair globals')
    for node in tree.body:
        if isinstance(node,ast.Expr):s.require(isinstance(node.value,ast.Constant) and isinstance(node.value.value,str),'Only module documentation expression')
    imports=[]
    for node in tree.body:
        if isinstance(node,ast.Import):imports.extend((alias.name,alias.asname) for alias in node.names)
        if isinstance(node,ast.ImportFrom):imports.extend((node.module+'.'+alias.name,alias.asname) for alias in node.names)
    s.require(imports==[('numpy','np'),('optimizer.complete',None)],'Explicit source repair dependencies')
    functions={node.name:node for node in tree.body if isinstance(node,ast.FunctionDef)}
    allowed={'edge_signs':({'np'},['nodes']),
        'imputed_magnitude':({'np','float'},['outgoing']),
        'recipient_repair':({'np','complete','imputed_magnitude','edge_signs'},['outgoing','options'])}
    result={}
    for name,(permitted,parameters) in allowed.items():
        node=functions[name]
        s.require([arg.arg for arg in node.args.args]==parameters and not node.args.defaults and node.args.vararg is None and node.args.kwarg is None,'Exact source primary API '+name)
        s.require(not any(isinstance(x,(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal)) for x in ast.walk(node)),'No dynamic source imports or globals')
        stored={x.id for x in ast.walk(node) if isinstance(x,ast.Name) and isinstance(x.ctx,ast.Store)}
        loaded={x.id for x in ast.walk(node) if isinstance(x,ast.Name) and isinstance(x.ctx,ast.Load)}
        external=loaded-stored-set(parameters)
        s.require(external==permitted,'Source primary external names '+name)
        # Whitelist used numpy operations; prevent a hidden file-loading dependency.
        numpy_calls={x.attr for x in ast.walk(node) if isinstance(x,ast.Attribute) and isinstance(x.value,ast.Name) and x.value.id=='np'}
        s.require(numpy_calls<=set(['stack','roll','abs','median','isfinite']),'Source numpy operations are array algebra only')
        result[name]=dict(parameters=parameters,external_names=sorted(external),numpy_operations=sorted(numpy_calls))
    return result


def run():
    base=s.HERE/'source/recipient/inputs'
    dependencies=inspect_tree((base/'repair.py').read_text())
    tree=ast.parse((base/'prepare.py').read_text());functions={x.name:x for x in tree.body if isinstance(x,ast.FunctionDef)}
    calls=[x for x in ast.walk(functions['checked_repair']) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='recipient_repair']
    s.require(len(calls)==1 and [ast.unparse(x) for x in calls[0].args]==['outgoing','options'] and not calls[0].keywords,'Source preparation invokes O-only repair')
    main=functions['prepare'];assignments=[x for x in ast.walk(main) if isinstance(x,ast.Assign)]
    values={target.id:node.value for node in assignments for target in node.targets if isinstance(target,ast.Name)}
    s.require(ast.unparse(values['out'])=="decode(old['packets'][:, 1])",'Only outgoing slot reaches source primary repair')
    s.require(ast.unparse(values['solutions'])=="[checked_repair(o, cfg['optimizer']) for o in out]",'No case metadata enters source primary repair')
    inherited=s.read(s.HERE/'source/recipient/inputs/SOURCE_REUSE.json')
    for name in ['optimizer.py','reader.py','sign_graph.py']:
        s.require(inherited[name]['use']=='unchanged' and s.sha(base/name)==inherited[name]['source_sha256'],'Source dependency identical to previously audited version')
    optimizer=ast.parse((base/'optimizer.py').read_text());complete=next(x for x in optimizer.body if isinstance(x,ast.FunctionDef) and x.name=='complete')
    s.require(ast.unparse(complete).count('PORTS[0]')==1 and 'donor' not in ast.unparse(complete),'Completion uses input pins only')
    return dict(status='PASS',source_dependency_inspection=dependencies,primary_preparation_path='old.packets[:,1] -> checked_repair(O, fixed optimizer options) -> recipient_repair(O, options)',
        previously_audited_unchanged_dependencies=['optimizer.py','reader.py','sign_graph.py'],source_functions_executed=False,
        boundary='Algorithmic dependency inspection and exact independent O-only reproduction; not filesystem blinding or source black-box perturbation.')
