// Problem Detail Page

var editor = null;
var currentFormalizationId = null;
var currentProblem = null;
var useFallback = false;
var hasUnsavedChanges = false;

// Lean 4 Syntax Highlighting Mode for CodeMirror
function initLeanMode(CodeMirror) {
    CodeMirror.defineMode('lean', function(config) {
        var keywords = [
            'def', 'theorem', 'lemma', 'axiom', 'axioms', 'constant', 'universe', 'universes',
            'inductive', 'structure', 'class', 'instance', 'attribute', 'namespace', 'end',
            'open', 'export', 'import', 'variable', 'variables', 'section', 'prefix', 'infix',
            'infixl', 'infixr', 'notation', 'macro', 'macro_rules', 'syntax', 'elab',
            'where', 'let', 'in', 'match', 'with', 'if', 'then', 'else', 'do', 'return',
            'for', 'while', 'repeat', 'until', 'break', 'continue',
            'fun', 'forall', 'exists', 'Type', 'Prop', 'Sort',
            'private', 'protected', 'partial', 'unsafe', 'noncomputable', 'mutual',
            'attribute', 'local', 'set_option', 'extends', 'deriving',
            'by', 'begin', 'have', 'show', 'suffices', 'assume', 'take', 'obtain',
            'rewrite', 'rw', 'simp', 'dsimp', 'simp_arith', 'simp only', 'simp at',
            'exact', 'refine', 'refine\'', 'apply', 'fapply', 'eapply', 'mapply', 'exact',
            'intro', 'intros', 'introv', 'rintro', 'rintros', 'revert', 'clear', 'rename',
            'cases', 'rcases', 'induction', 'destruct', 'contradiction', 'exfalso',
            'split', 'left', 'right', 'constructor', 'existsi', 'use', 'refine',
            'unfold', 'unfold_projs', 'unfold_let', 'delta', 'change', 'convert', 'convert_to',
            'transitivity', 'symmetry', 'reflexivity', 'refl', 'rfl', 'congr', 'congr_n',
            'trivial', 'true', 'false', 'and', 'or', 'not', 'iff', 'implies',
            'decide', 'native_decide', 'norm_cast', 'push_cast', 'norm_num', 'ring', 'omega',
            'linarith', 'ring_nf', 'field_simp', 'field', 'sorry', 'admit', 'done',
            'trace', 'sleep', 'run_cmd', '#check', '#eval', '#reduce', '#print', '#help',
            'calc', 'haveI', 'letI', 'infer_instance', 'classical', 'choose', 'choose!',
            'obtain', 'rcases', 'rintro', 'rintros', 'casesm', 'rcases?', 'rintro?',
            'all_goals', 'any_goals', 'focus', 'skip', 'try', 'fail', 'fail_if_success',
            'success_if_fail', 'guard_expr', 'guard_target', 'guard_hyp', 'tactic',
            'library_note', 'add_tactic_doc', 'add_decl_doc'
        ];

        var types = [
            'Nat', 'Int', 'Real', 'Bool', 'String', 'Char', 'List', 'Option', 'Sum',
            'Prod', 'Sigma', 'Subtype', 'Fin', 'Empty', 'Unit', 'PUnit',
            'True', 'False', 'And', 'Or', 'Not', 'Iff', 'Eq', 'HEq', 'Ne',
            'Empty', 'PEmpty', 'Plift', 'Uliftr', 'Set', 'Function', 'Relation'
        ];

        var constants = [
            'true', 'false', 'none', 'some', 'inl', 'inr', 'nil', 'cons', 'zero', 'succ'
        ];

        function isKeyword(word) {
            return keywords.indexOf(word) >= 0;
        }

        function isType(word) {
            return types.indexOf(word) >= 0;
        }

        function isConstant(word) {
            return constants.indexOf(word) >= 0;
        }

        return {
            startState: function() {
                return { commentDepth: 0 };
            },
            token: function(stream, state) {
                // Handle block comments
                if (state.commentDepth > 0) {
                    if (stream.match(/-\//)) {
                        state.commentDepth--;
                        return 'comment';
                    }
                    if (stream.match(/\/-/)) {
                        state.commentDepth++;
                        return 'comment';
                    }
                    stream.next();
                    return 'comment';
                }

                // Block comment start
                if (stream.match('/-')) {
                    state.commentDepth++;
                    return 'comment';
                }

                // Line comment
                if (stream.match(/--.*$/)) {
                    return 'comment';
                }

                // String literals
                if (stream.match(/"/)) {
                    var escaped = false;
                    while (!stream.eol()) {
                        var ch = stream.next();
                        if (ch === '\\' && !escaped) {
                            escaped = true;
                        } else if (ch === '"' && !escaped) {
                            break;
                        } else {
                            escaped = false;
                        }
                    }
                    return 'string';
                }

                // Character literals
                if (stream.match(/'.'/)) {
                    return 'string';
                }
                if (stream.match(/'\\.'/)) {
                    return 'string';
                }

                // Numbers
                if (stream.match(/[0-9]+(\.[0-9]+)?/)) {
                    return 'number';
                }

                // Identifiers and keywords
                if (stream.match(/[a-zA-Z_][a-zA-Z0-9_']*/)) {
                    var word = stream.current();
                    if (isKeyword(word)) {
                        return 'keyword';
                    }
                    if (isType(word)) {
                        return 'type';
                    }
                    if (isConstant(word)) {
                        return 'atom';
                    }
                    return 'variable-2';
                }

                // Type annotations and arrows
                if (stream.match(/->|→/)) {
                    return 'operator';
                }
                if (stream.match(/<-|←/)) {
                    return 'operator';
                }
                if (stream.match(/=>|⟹/)) {
                    return 'operator';
                }

                // Special symbols
                if (stream.match(/[∀∃λ∧∨¬↔≤≥≠×÷]/)) {
                    return 'builtin';
                }

                // Operators
                if (stream.match(/[+\-*\/<>=!&|^~@#$%?:]+/)) {
                    return 'operator';
                }

                // Brackets
                if (stream.match(/[(){}\[\]⟨⟩]/)) {
                    return 'bracket';
                }

                // Punctuation
                if (stream.match(/[.,;:]/)) {
                    return 'punctuation';
                }

                // Skip unknown characters
                stream.next();
                return null;
            }
        };
    });
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing...');
    console.log('problemId:', typeof problemId !== 'undefined' ? problemId : 'undefined');
    console.log('problemData:', typeof problemData !== 'undefined' ? problemData : 'undefined');

    currentProblem = problemData;

    // Check if CodeMirror loaded
    if (typeof CodeMirror === 'undefined') {
        console.warn('CodeMirror not loaded, using fallback textarea');
        useFallback = true;
        document.querySelector('.editor-container').style.display = 'none';
        document.getElementById('editorFallback').style.display = 'block';
    } else {
        // Initialize Lean 4 mode
        initLeanMode(CodeMirror);

        var textarea = document.getElementById('leanEditor');
        if (!textarea) {
            console.error('Editor textarea not found!');
            return;
        }

        try {
            editor = CodeMirror.fromTextArea(textarea, {
                mode: 'lean',
                theme: 'dracula',
                lineNumbers: true,
                indentUnit: 2,
                tabSize: 2,
                lineWrapping: true,
                matchBrackets: true,
                autoCloseBrackets: true,
                extraKeys: {
                    'Tab': function(cm) {
                        if (cm.somethingSelected()) {
                            cm.indentSelection('add');
                        } else {
                            cm.replaceSelection('  ', 'end');
                        }
                    },
                    'Ctrl-S': function(cm) { saveCode(); },
                    'Cmd-S': function(cm) { saveCode(); },
                    'Ctrl-Enter': function(cm) { generateFormalization('formalize'); },
                    'Cmd-Enter': function(cm) { generateFormalization('formalize'); },
                    'Ctrl-Shift-Enter': function(cm) { checkCode(); },
                    'Cmd-Shift-Enter': function(cm) { checkCode(); }
                }
            });
            console.log('CodeMirror initialized successfully');

            // Track changes
            editor.on('change', function() {
                hasUnsavedChanges = true;
                document.getElementById('saveCodeBtn').disabled = false;
            });

            // Force refresh after a short delay
            setTimeout(function() {
                if (editor) editor.refresh();
            }, 100);
        } catch (e) {
            console.error('CodeMirror init error:', e);
            useFallback = true;
            document.querySelector('.editor-container').style.display = 'none';
            document.getElementById('editorFallback').style.display = 'block';
            
            // Add change tracking for fallback editor
            var fallbackEditor = document.getElementById('leanEditorFallback');
            if (fallbackEditor) {
                fallbackEditor.addEventListener('input', function() {
                    hasUnsavedChanges = true;
                    document.getElementById('saveCodeBtn').disabled = false;
                });
            }
        }
    }
    
    // Event listeners
    var generateBtn = document.getElementById('generateBtn');
    var improveBtn = document.getElementById('improveBtn');
    var fixBtn = document.getElementById('fixBtn');
    var saveCodeBtn = document.getElementById('saveCodeBtn');
    var checkCodeBtn = document.getElementById('checkCodeBtn');
    
    if (generateBtn) {
        generateBtn.addEventListener('click', function() { 
            console.log('Generate clicked');
            generateFormalization('formalize'); 
        });
    }
    
    if (improveBtn) {
        improveBtn.addEventListener('click', function() { 
            generateFormalization('improve'); 
        });
    }
    
    if (fixBtn) {
        fixBtn.addEventListener('click', function() { 
            generateFormalization('fix'); 
        });
    }
    
    if (saveCodeBtn) {
        saveCodeBtn.addEventListener('click', saveCode);
    }
    
    if (checkCodeBtn) {
        checkCodeBtn.addEventListener('click', checkCode);
    }
    
    // Load latest formalization if exists
    if (typeof formalizationsData !== 'undefined' && formalizationsData && formalizationsData.length > 0) {
        loadFormalization(formalizationsData[0].id);
    }
    
    console.log('Initialization complete');
});

function setEditorValue(code) {
    if (useFallback) {
        var fallback = document.getElementById('leanEditorFallback');
        fallback.value = code;
    } else if (editor) {
        editor.setValue(code);
        editor.refresh();
    }
}

function getEditorValue() {
    if (useFallback) {
        return document.getElementById('leanEditorFallback').value;
    } else if (editor) {
        return editor.getValue();
    }
    return '';
}

function generateFormalization(action) {
    console.log('generateFormalization called with action:', action);
    
    // Show loading state
    setOutput('<span class="loading"></span> Generating...', '', true);
    
    document.getElementById('generateBtn').disabled = true;
    document.getElementById('improveBtn').disabled = true;
    document.getElementById('fixBtn').disabled = true;
    
    var code = getEditorValue();
    var provider = document.getElementById('llmStatus').textContent.toLowerCase();
    
    // Use streaming for Grok/xAI
    if (provider === 'grok' || provider === 'xai') {
        generateWithStream(action, code);
    } else {
        generateWithoutStream(action, code);
    }
}

function generateWithStream(action, code) {
    var fullCode = '';
    
    fetch('/api/formalize-stream/' + problemId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            code: code,
            action: action
        })
    }).then(function(response) {
        if (!response.ok) {
            throw new Error('HTTP error ' + response.status);
        }
        
        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';
        
        function read() {
            return reader.read().then(function(result) {
                if (result.done) {
                    finishGeneration();
                    return;
                }
                
                buffer += decoder.decode(result.value, { stream: true });
                var lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer
                
                lines.forEach(function(line) {
                    if (line.startsWith('data: ')) {
                        try {
                            var data = JSON.parse(line.substring(6));
                            
                            if (data.delta) {
                                fullCode += data.delta;
                                setEditorValue(fullCode);
                            }
                            
                            if (data.done) {
                                currentFormalizationId = data.id;
                                var formStatus = document.getElementById('formStatus');
                                if (formStatus) formStatus.textContent = '#' + data.id;
                                document.getElementById('saveCodeBtn').disabled = true;
                                setOutput('Formalization generated!', 'success');
                                loadHistory();
                            }
                            
                            if (data.error) {
                                setOutput('Error: ' + data.error, 'error');
                            }
                            
                            if (data.id && data.lean_code && !data.done) {
                                // Non-streaming response (mock mode)
                                setEditorValue(data.lean_code);
                                currentFormalizationId = data.id;
                                var formStatus = document.getElementById('formStatus');
                                if (formStatus) formStatus.textContent = '#' + data.id;
                                document.getElementById('saveCodeBtn').disabled = true;
                                setOutput('Formalization generated!', 'success');
                                loadHistory();
                            }
                        } catch (e) {
                            console.log('Parse error:', e, 'for line:', line);
                        }
                    }
                });
                
                return read();
            });
        }
        
        return read();
    }).catch(function(err) {
        console.error('Error:', err);
        setOutput('Error: ' + err.message, 'error');
        finishGeneration();
    });
}

function generateWithoutStream(action, code) {
    console.log('Sending request to /api/formalize/' + problemId);
    
    fetch('/api/formalize/' + problemId, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            code: code,
            action: action
        })
    })
    .then(function(res) { 
        console.log('Response received:', res.status);
        return res.json(); 
    })
    .then(function(result) {
        console.log('Result:', result);
        console.log('Lean code length:', result.lean_code ? result.lean_code.length : 0);
        
        setEditorValue(result.lean_code);
        currentFormalizationId = result.id;
        
        var formStatus = document.getElementById('formStatus');
        if (formStatus) formStatus.textContent = '#' + result.id;
        
        document.getElementById('saveCodeBtn').disabled = true;
        setOutput('Formalization generated!', 'success');
        loadHistory();
    })
    .catch(function(err) {
        console.error('Error:', err);
        setOutput('Error: ' + err.message, 'error');
    })
    .finally(function() {
        finishGeneration();
    });
}

function finishGeneration() {
    document.getElementById('generateBtn').disabled = false;
    document.getElementById('improveBtn').disabled = false;
    document.getElementById('fixBtn').disabled = false;
}

function saveCode() {
    if (!currentFormalizationId) {
        alert('No formalization to save. Generate one first.');
        return;
    }
    
    fetch('/api/formalization/' + currentFormalizationId, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: getEditorValue() })
    })
    .then(function(res) { return res.json(); })
    .then(function() {
        document.getElementById('saveCodeBtn').disabled = true;
        setOutput('Saved successfully!', 'success');
        loadHistory();
    })
    .catch(function(err) {
        alert('Error saving: ' + err.message);
    });
}

function checkCode() {
    setOutput('Checking...', '');
    
    fetch('/api/check_lean', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: getEditorValue() })
    })
    .then(function(res) { return res.json(); })
    .then(function(result) {
        if (result.error === 'lean_not_found') {
            setOutput('Lean is not installed. Install from https://leanprover.github.io/', 'warning');
        } else if (result.success) {
            setOutput('No errors found!', 'success');
        } else {
            setOutput('Errors:\n' + result.output, 'error');
        }
    })
    .catch(function(err) {
        setOutput('Error: ' + err.message, 'error');
    });
}

function loadFormalization(id) {
    fetch('/api/problem/' + problemId)
        .then(function(res) { return res.json(); })
        .then(function(problem) {
            var form = problem.formalizations.find(function(f) { return f.id === id; });
            if (form) {
                setEditorValue(form.lean_code);
                currentFormalizationId = id;
                var formStatus = document.getElementById('formStatus');
                if (formStatus) formStatus.textContent = '#' + id;
                document.getElementById('saveCodeBtn').disabled = true;
            }
        });
}

function loadHistory() {
    fetch('/api/problem/' + problemId)
        .then(function(res) { return res.json(); })
        .then(function(problem) {
            var list = document.getElementById('historyList');
            var forms = problem.formalizations || [];
            
            if (forms.length === 0) {
                list.innerHTML = '<p class="placeholder">Previous versions will appear here</p>';
                return;
            }
            
            var html = '';
            forms.forEach(function(f) {
                html += '<div class="history-item" data-id="' + f.id + '">' +
                    '<span class="history-status">' + f.status + '</span>' +
                    '<span class="history-time">' + new Date(f.updated_at).toLocaleString() + '</span>' +
                    '<div class="history-actions">' +
                    '<button class="btn btn-small btn-primary" onclick="loadFormalization(' + f.id + ')">Load</button>' +
                    '<button class="btn btn-small btn-delete" onclick="deleteFormalization(' + f.id + ')">Delete</button>' +
                    '</div>' +
                    '</div>';
            });
            list.innerHTML = html;
        })
        .catch(function(err) {
            console.error('Error loading history:', err);
        });
}

function deleteFormalization(id) {
    if (!confirm('Are you sure you want to delete this formalization?')) return;
    
    fetch('/api/formalization/' + id, { method: 'DELETE' })
        .then(function(res) { return res.json(); })
        .then(function() {
            loadHistory();
            setOutput('Formalization deleted', 'success');
        })
        .catch(function(err) {
            setOutput('Error deleting: ' + err.message, 'error');
        });
}

function setOutput(text, type, allowHtml) {
    var output = document.getElementById('outputContent');
    if (output) {
        var content = allowHtml ? text : escapeHtml(text);
        output.innerHTML = '<p class="' + (type || '') + '">' + content + '</p>';
    }
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
