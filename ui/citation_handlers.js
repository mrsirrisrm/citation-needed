// Citation Needed - Interactive JavaScript handlers
console.log('🚀 Citation Needed: Loading JavaScript from external file');

// Global debug function
window.citationDebug = function() {
    console.log('🔍 Debug info:', {
        toggleComment: typeof window.toggleComment,
        highlightCitation: typeof window.highlightCitation,
        location: window.location.href,
        citationElements: document.querySelectorAll('.citation-comment').length,
        highlightElements: document.querySelectorAll('.citation-highlight').length,
        documentReadyState: document.readyState,
        gradioElements: document.querySelectorAll('.gradio-container').length
    });
};

// Toggle comment display
window.toggleComment = function(citationId) {
    console.log('🔄 Toggling comment for:', citationId);
    const content = document.getElementById('content_' + citationId);
    const icon = document.getElementById('icon_' + citationId);

    if (!content || !icon) {
        console.warn('❌ Elements not found for citation:', citationId);
        console.log('🔍 Available elements:', {
            allContentElements: document.querySelectorAll('[id^="content_"]').length,
            allIconElements: document.querySelectorAll('[id^="icon_"]').length,
            lookingFor: ['content_' + citationId, 'icon_' + citationId]
        });
        return;
    }

    console.log('✅ Found elements, toggling display');
    if (content.style.display === 'block') {
        content.style.display = 'none';
        icon.textContent = '▼';
        icon.classList.remove('expanded');
        console.log('📝 Collapsed comment');
    } else {
        content.style.display = 'block';
        icon.textContent = '▲';
        icon.classList.add('expanded');
        console.log('📝 Expanded comment');
    }
};

// Highlight citation
window.highlightCitation = function(citationId) {
    console.log('🎯 Highlighting citation:', citationId);

    // Remove previous highlights
    document.querySelectorAll('.citation-highlight').forEach(el => {
        el.classList.remove('active-highlight');
    });

    // Add highlight to target
    const citation = document.getElementById(citationId);
    if (citation) {
        citation.classList.add('active-highlight');
        citation.scrollIntoView({ behavior: 'smooth', block: 'center' });
        console.log('✨ Citation highlighted');
    } else {
        console.warn('❌ Citation element not found:', citationId);
        console.log('🔍 Available citation elements:', {
            allCitations: document.querySelectorAll('[data-citation-id]').length,
            availableIds: Array.from(document.querySelectorAll('[data-citation-id]')).map(el => el.getAttribute('data-citation-id'))
        });
    }
};

// Set up event delegation for dynamic content
function setupEventDelegation() {
    console.log('🎯 Setting up event delegation');

    // Remove existing listener to avoid duplicates
    if (window.citationClickHandler) {
        document.removeEventListener('click', window.citationClickHandler);
        console.log('🔄 Removed existing event listener');
    }

    // Create new click handler
    window.citationClickHandler = function(event) {
        // Handle comment header clicks
        const header = event.target.closest('.comment-header');
        if (header) {
            console.log('📱 Comment header clicked via event delegation');
            const citationComment = header.closest('.citation-comment');
            if (citationComment) {
                const citationId = citationComment.getAttribute('data-citation-id');
                if (citationId) {
                    window.toggleComment(citationId);
                    event.preventDefault();
                    event.stopPropagation();
                }
            } else {
                console.warn('❌ Citation comment container not found for header');
            }
            return;
        }

        // Handle citation highlight clicks
        const citation = event.target.closest('.citation-highlight');
        if (citation) {
            console.log('🔗 Citation clicked via event delegation');
            const citationId = citation.getAttribute('data-citation-id');
            if (citationId) {
                window.highlightCitation(citationId);

                // Scroll to and expand corresponding comment
                const comment = document.querySelector(`.citation-comment[data-citation-id="${citationId}"]`);
                if (comment) {
                    comment.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    const content = document.getElementById('content_' + citationId);
                    if (content && content.style.display !== 'block') {
                        window.toggleComment(citationId);
                    }
                } else {
                    console.warn('❌ Corresponding comment not found for citation:', citationId);
                }
                event.preventDefault();
                event.stopPropagation();
            }
        }
    };

    // Add the event listener
    document.addEventListener('click', window.citationClickHandler);
    console.log('✅ Event delegation setup complete');
}

// Set up mutation observer for dynamic content
function setupMutationObserver() {
    console.log('🔬 Setting up mutation observer for dynamic content');

    const observer = new MutationObserver(function(mutations) {
        let hasCitationContent = false;

        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    // Check if this node or its children contain citation elements
                    if (node.querySelector && (
                        node.querySelector('.citation-comment') ||
                        node.querySelector('.citation-highlight') ||
                        node.classList.contains('citation-comment') ||
                        node.classList.contains('citation-highlight')
                    )) {
                        hasCitationContent = true;
                    }
                }
            });
        });

        if (hasCitationContent) {
            console.log('🆕 New citation content detected, re-initializing');
            setupEventDelegation();
            window.citationDebug();
        }
    });

    // Start observing the document body for changes
    observer.observe(document.body, {
        childList: true,
        subtree: true,
        attributes: false,
        characterData: false
    });

    console.log('✅ Mutation observer setup complete');
    return observer;
}

// Initialize when DOM is ready
function initializeCitationSystem() {
    console.log('🎬 Initializing citation system');
    console.log('📋 Document ready state:', document.readyState);

    try {
        setupEventDelegation();
        setupMutationObserver();
        window.citationDebug();
        console.log('🎉 Citation system ready! Run window.citationDebug() to check status');
    } catch (error) {
        console.error('❌ Error during citation system initialization:', error);
    }
}

// Multiple initialization attempts for reliability
if (document.readyState === 'loading') {
    console.log('📄 Document still loading, waiting for DOMContentLoaded');
    document.addEventListener('DOMContentLoaded', initializeCitationSystem);
} else {
    console.log('📄 Document already loaded, initializing immediately');
    initializeCitationSystem();
}

// Also try after multiple delays for Gradio's dynamic loading
setTimeout(initializeCitationSystem, 500);
setTimeout(initializeCitationSystem, 1000);
setTimeout(initializeCitationSystem, 2000);

// Handle page visibility changes to reinitialize when tab becomes active
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        console.log('👁️ Page became visible, re-initializing citation system');
        initializeCitationSystem();
    }
});

// Export for debugging
window.initializeCitationSystem = initializeCitationSystem;

console.log('✅ Citation Needed JavaScript loaded successfully');
console.log('💡 Debug commands available: window.citationDebug(), window.initializeCitationSystem()');