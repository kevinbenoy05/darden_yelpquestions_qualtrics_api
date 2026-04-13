// Multi-Review Qualtrics Annotation Tool - 6 Reviews
// Paste this code in the JavaScript section of your Qualtrics question

Qualtrics.SurveyEngine.addOnReady(function() {
    var that = this;

    // List of attributes for annotation
    var attributes = [
        'Atmosphere',
        'Cleanliness/sanitary condition',
        'Customer service (including promptness)',
        'Family friendliness',
        'Food accommodation/customization',
        'Healthiness',
        'Location',
        'Opening hours',
        'Parking options',
        'Price',
        'Quality of drink',
        'Quality of food',
        'Reservation system',
        'Restaurant size/space',
        'Seating options',
        'Sustainability',
        'Time to get seated',
        'Type of cuisine',
        'Variety of drink menu',
        'Variety of food menu',
        'Portion size'
    ];

    var attributeDefinitions = {
        'Atmosphere': 'The overall vibe, mood, or feeling of the restaurant environment.',
        'Cleanliness/sanitary condition': 'The sanitary condition of the dining area, restrooms, utensils, and floors.',
        'Customer service (including promptness)': 'Staff behavior, friendliness, and the speed of service (e.g., promptness).',
        'Family friendliness': 'Suitability for children, including safety (e.g., no sharp objects and kid-friendly menu options).',
        'Food accommodation/customization': 'The kitchen’s willingness/ability to modify dishes beyond standard menu options for health or religious reasons.',
        'Healthiness': 'The nutritional value and wholesomeness of the food options.',
        'Location': 'Convenience of the physical address and accessibility (e.g., near landmarks, easy to find).',
        'Opening hours': 'Convenience of the operating times (e.g., open late, open for breakfast).',
        'Parking options': 'Ease and availability of parking near the restaurant.',
        'Price': 'The fairness of the price paid relative to the quality and amount of food received.',
        'Quality of drink': 'The taste, freshness, and preparation standard of the beverages.',
        'Quality of food': 'The taste, freshness, and preparation standard of the meals.',
        'Reservation system': 'The ease and convenience of booking a table or event.',
        'Restaurant size/space': 'Comfort of the physical space (e.g., not overcrowded) and capacity to seat guests without long waits.',
        'Seating options': 'Availability of different seating types (booths, tables) and accessibility for those with disabilities.',
        'Sustainability': 'Visible commitment to eco-friendly practices (e.g., reclaimed furniture, no plastic, digital menus).',
        'Time to get seated': 'The wait time to get a table upon arrival, distinct from food serving speed.',
        'Type of cuisine': 'The specific ethnic, regional, or national style of cooking offered (e.g., Thai, Italian).',
        'Variety of drink menu': 'The range of beverage options available (alcohol, soft drinks, juices, etc.).',
        'Variety of food menu': 'The range of different food options available to choose from.',
        'Portion size': 'The amount of food served for a given dish.'
    };

    // Reviews from embedded data
    var reviews = [
        Qualtrics.SurveyEngine.getEmbeddedData('Review1') || '',
        Qualtrics.SurveyEngine.getEmbeddedData('Review2') || '',
        Qualtrics.SurveyEngine.getEmbeddedData('Review3') || '',
        Qualtrics.SurveyEngine.getEmbeddedData('Review4') || '',
        Qualtrics.SurveyEngine.getEmbeddedData('Review5') || '',
        Qualtrics.SurveyEngine.getEmbeddedData('Review6') || ''
    ];

    // Global variables
    var currentReviewIndex = 0;
    var annotations = [];
    var selectedText = '';
    var selectedRange = null;
    var allResults = [];
    var annotationOrder = 0;
    var deletedAnnotations = [];
    var deletionOrder = 0;
    var selectionChangeBound = false;

    // Tooltip state
    var tooltipEl = null;
    var tooltipTimer = null;
    var tooltipDelayMs = 500;

    function ensureTooltipEl() {
        if (!tooltipEl) tooltipEl = document.getElementById('attrTooltip');
        return tooltipEl;
    }

    function showAttrTooltip(targetEl, attr) {
        var def = attributeDefinitions[attr];
        if (!def) return;

        var el = ensureTooltipEl();
        if (!el) return;

        el.innerHTML = '<div>' + escapeHtml(def) + '</div>';
        el.style.display = 'block';
        positionTooltip(targetEl, el);
    }

    function hideAttrTooltip() {
        var el = ensureTooltipEl();
        if (!el) return;
        el.style.display = 'none';
        el.classList.remove('below');
    }

    function positionTooltip(targetEl, tooltip) {
        var margin = 10;
        var rect = targetEl.getBoundingClientRect();

        tooltip.style.left = '0px';
        tooltip.style.top = '0px';

        var tipRect = tooltip.getBoundingClientRect();

        var top = rect.top - tipRect.height - 12;
        var left = rect.left + (rect.width / 2) - (tipRect.width / 2);

        left = Math.max(margin, Math.min(left, window.innerWidth - tipRect.width - margin));

        if (top < margin) {
            top = rect.bottom + 12;
            tooltip.classList.add('below');
        } else {
            tooltip.classList.remove('below');
        }

        top = Math.max(margin, Math.min(top, window.innerHeight - tipRect.height - margin));

        tooltip.style.left = left + 'px';
        tooltip.style.top = top + 'px';
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function createInterface() {
        var container = document.createElement('div');
        container.className = 'annotation-container';
        container.innerHTML =
            '<style>' +
                '.attr-tooltip {' +
                    'position: fixed;' +
                    'z-index: 99999;' +
                    'max-width: 320px;' +
                    'background: rgba(33, 37, 41, 0.95);' +
                    'color: #fff;' +
                    'padding: 10px 12px;' +
                    'border-radius: 8px;' +
                    'box-shadow: 0 10px 30px rgba(0,0,0,0.25);' +
                    'font-size: 12.5px;' +
                    'line-height: 1.35;' +
                    'display: none;' +
                    'pointer-events: none;' +
                '}' +
                '.attr-tooltip::after {' +
                    'content: "";' +
                    'position: absolute;' +
                    'left: 50%;' +
                    'transform: translateX(-50%);' +
                    'border: 7px solid transparent;' +
                    'border-top-color: rgba(33, 37, 41, 0.95);' +
                    'bottom: -14px;' +
                '}' +
                '.attr-tooltip.below::after {' +
                    'border-top-color: transparent;' +
                    'border-bottom-color: rgba(33, 37, 41, 0.95);' +
                    'top: -14px;' +
                    'bottom: auto;' +
                '}' +

                '.annotation-container {' +
                    'font-family: Arial, sans-serif;' +
                    'max-width: 1200px;' +
                    'margin: 0 auto;' +
                '}' +

                '.progress-section {' +
                    'background: #f8f9fa;' +
                    'padding: 15px;' +
                    'border-radius: 8px;' +
                    'margin-bottom: 20px;' +
                    'border: 2px solid #e9ecef;' +
                '}' +
                '.progress-bar {' +
                    'width: 100%;' +
                    'height: 20px;' +
                    'background: #e9ecef;' +
                    'border-radius: 10px;' +
                    'overflow: hidden;' +
                    'margin-bottom: 10px;' +
                '}' +
                '.progress-fill {' +
                    'height: 100%;' +
                    'background: linear-gradient(90deg, #28a745, #20c997);' +
                    'transition: width 0.3s ease;' +
                '}' +
                '.progress-text {' +
                    'text-align: center;' +
                    'font-weight: bold;' +
                    'color: #333;' +
                '}' +

                '.instruction-section {' +
                    'background: #f8f9fa;' +
                    'padding: 20px;' +
                    'border-radius: 8px;' +
                    'margin-bottom: 20px;' +
                    'border: 2px solid #e9ecef;' +
                    'text-align: center;' +
                '}' +
                '.instruction-section h3 {' +
                    'margin: 0 0 10px 0;' +
                    'color: #333;' +
                '}' +

                '.work-area {' +
                    'display: flex;' +
                    'gap: 20px;' +
                    'margin-bottom: 20px;' +
                '}' +
                '.review-panel {' +
                    'flex: 1;' +
                    'background: white;' +
                    'border: 2px solid #ddd;' +
                    'border-radius: 8px;' +
                    'padding: 20px;' +
                '}' +
                '.review-text {' +
                    'line-height: 1.6;' +
                    'font-size: 16px;' +
                    'user-select: text;' +
                    'cursor: text;' +
                    'min-height: 300px;' +
                    'white-space: pre-wrap;' +
                    'word-break: break-word;' +
                '}' +
                '.attributes-panel {' +
                    'flex: 1;' +
                    'background: white;' +
                    'border: 2px solid #ddd;' +
                    'border-radius: 8px;' +
                    'padding: 20px;' +
                '}' +
                '.attribute-list {' +
                    'display: grid;' +
                    'grid-template-columns: 1fr 1fr;' +
                    'gap: 8px;' +
                '}' +
                '.attribute-btn {' +
                    'padding: 10px 15px;' +
                    'border: 1px solid #ccc;' +
                    'background: white;' +
                    'border-radius: 5px;' +
                    'cursor: pointer;' +
                    'text-align: left;' +
                    'font-size: 14px;' +
                    'transition: all 0.2s;' +
                '}' +
                '.attribute-btn:hover {' +
                    'background: #f0f0f0;' +
                    'border-color: #007bff;' +
                '}' +
                '.attribute-btn.selected {' +
                    'background: #007bff;' +
                    'color: white;' +
                    'border-color: #0056b3;' +
                '}' +

                '.highlight {' +
                    'background-color: #fff3cd;' +
                    'border-radius: 3px;' +
                    'padding: 1px 2px;' +
                    'border-bottom: 2px solid #ffc107;' +
                '}' +

                '.results-section {' +
                    'background: white;' +
                    'border: 2px solid #ddd;' +
                    'border-radius: 8px;' +
                    'padding: 20px;' +
                    'margin-bottom: 20px;' +
                    'min-height: 150px;' +
                '}' +
                '.results-list {' +
                    'max-height: 250px;' +
                    'overflow-y: auto;' +
                '}' +
                '.result-item {' +
                    'display: flex;' +
                    'justify-content: space-between;' +
                    'align-items: flex-start;' +
                    'padding: 10px;' +
                    'margin: 5px 0;' +
                    'background: #f8f9fa;' +
                    'border-radius: 5px;' +
                    'border-left: 3px solid #007bff;' +
                '}' +
                '.result-content {' +
                    'flex: 1;' +
                    'margin-right: 10px;' +
                '}' +
                '.result-attribute {' +
                    'font-weight: bold;' +
                    'color: #007bff;' +
                    'margin-bottom: 3px;' +
                '}' +
                '.result-text {' +
                    'color: #666;' +
                    'font-size: 14px;' +
                    'font-style: italic;' +
                '}' +
                '.delete-btn {' +
                    'background: #dc3545;' +
                    'color: white;' +
                    'border: none;' +
                    'padding: 5px 10px;' +
                    'border-radius: 3px;' +
                    'cursor: pointer;' +
                    'font-size: 12px;' +
                '}' +
                '.delete-btn:hover {' +
                    'background: #c82333;' +
                '}' +

                '.navigation-section {' +
                    'text-align: center;' +
                    'padding: 20px;' +
                '}' +
                '.next-btn {' +
                    'background: #28a745;' +
                    'color: white;' +
                    'border: none;' +
                    'padding: 15px 30px;' +
                    'border-radius: 8px;' +
                    'cursor: pointer;' +
                    'font-size: 16px;' +
                    'font-weight: bold;' +
                    'transition: background 0.2s;' +
                '}' +
                '.next-btn:hover {' +
                    'background: #218838;' +
                '}' +
                '.next-btn:disabled {' +
                    'background: #6c757d;' +
                    'cursor: not-allowed;' +
                '}' +
                '.complete-btn {' +
                    'background: #007bff;' +
                    'color: white;' +
                    'border: none;' +
                    'padding: 15px 30px;' +
                    'border-radius: 8px;' +
                    'cursor: pointer;' +
                    'font-size: 16px;' +
                    'font-weight: bold;' +
                '}' +
                '.complete-btn:hover {' +
                    'background: #0056b3;' +
                '}' +
                '.completion-message {' +
                    'background: #d4edda;' +
                    'border: 1px solid #c3e6cb;' +
                    'border-radius: 8px;' +
                    'padding: 20px;' +
                    'margin: 20px 0;' +
                    'text-align: center;' +
                    'color: #155724;' +
                    'display: none;' +
                '}' +
                '.status-text {' +
                    'color: #666;' +
                    'font-style: italic;' +
                    'text-align: center;' +
                    'padding: 20px;' +
                '}' +
                '.panel-title {' +
                    'margin: 0 0 15px 0;' +
                    'color: #333;' +
                    'font-size: 18px;' +
                    'font-weight: bold;' +
                '}' +
                '@media (max-width: 768px) {' +
                    '.work-area {' +
                        'flex-direction: column;' +
                    '}' +
                '}' +
            '</style>' +

            '<div class="progress-section">' +
                '<div class="progress-bar">' +
                    '<div class="progress-fill" id="progressFill"></div>' +
                '</div>' +
                '<div class="progress-text" id="progressText">Review 1 of 6</div>' +
            '</div>' +

            '<div class="instruction-section">' +
                '<h3 id="instructionTitle">Restaurant Review Annotation Tool</h3>' +
                '<p>You will annotate <strong>6 restaurant reviews</strong> in total. For each review:</p>' +
                '<p><strong>Process:</strong> Highlight text → Click attributes → Review your selections → Move to next review</p>' +
            '</div>' +

            '<div class="work-area" id="workArea">' +
                '<div class="review-panel">' +
                    '<h4 class="panel-title" id="reviewTitle">Review 1 (Click and drag to select text)</h4>' +
                    '<div class="review-text" id="reviewText"></div>' +
                '</div>' +

                '<div class="attributes-panel">' +
                    '<h4 class="panel-title">Select Attributes</h4>' +
                    '<div class="attribute-list" id="attributeList"></div>' +
                '</div>' +
            '</div>' +

            '<div class="results-section" id="resultsSection">' +
                '<h4 class="panel-title">Current Annotations (<span id="annotationCount">0</span>)</h4>' +
                '<div class="results-list" id="resultsList">' +
                    '<div class="status-text">No annotations yet. Select text and choose attributes above!</div>' +
                '</div>' +
            '</div>' +

            '<div class="navigation-section" id="navigationSection">' +
                '<button class="next-btn" id="nextBtn" onclick="window.moveToNextReview()">Save & Move to Next Review</button>' +
            '</div>' +

            '<div class="completion-message" id="completionMessage">' +
                '<h3>All Reviews Completed!</h3>' +
                '<p>Thank you for annotating all 6 reviews. Your data has been saved successfully.</p>' +
                '<button class="complete-btn" onclick="window.finishSurvey()">Save Data</button>' +
            '</div>' +

            '<div class="attr-tooltip" id="attrTooltip"></div>';

        return container;
    }

    function initialize() {
        var container = createInterface();
        that.questionContainer.appendChild(container);

        var attributeList = document.getElementById('attributeList');
        attributes.forEach(function(attr) {
            var btn = document.createElement('button');
            btn.className = 'attribute-btn';
            btn.type = 'button';
            btn.textContent = attr;

            btn.removeAttribute('title');

            btn.addEventListener('mouseenter', function() {
                clearTimeout(tooltipTimer);
                tooltipTimer = setTimeout(function() {
                    showAttrTooltip(btn, attr);
                }, tooltipDelayMs);
            });

            btn.addEventListener('mouseleave', function() {
                clearTimeout(tooltipTimer);
                hideAttrTooltip();
            });

            btn.addEventListener('mousemove', function() {
                var el = ensureTooltipEl();
                if (el && el.style.display === 'block') positionTooltip(btn, el);
            });

            btn.addEventListener('focus', function() {
                clearTimeout(tooltipTimer);
                tooltipTimer = setTimeout(function() {
                    showAttrTooltip(btn, attr);
                }, tooltipDelayMs);
            });

            btn.addEventListener('blur', function() {
                clearTimeout(tooltipTimer);
                hideAttrTooltip();
            });

            btn.onclick = function() {
                selectAttribute(attr, btn);
            };

            attributeList.appendChild(btn);
        });

        window.addEventListener('scroll', hideAttrTooltip, true);
        window.addEventListener('resize', hideAttrTooltip);

        if (!selectionChangeBound) {
            document.addEventListener('selectionchange', function() {
                var selection = window.getSelection();
                if (!selection || selection.rangeCount === 0 || selection.toString().trim() === '') {
                    selectedText = '';
                    selectedRange = null;
                }
            });
            selectionChangeBound = true;
        }

        loadReview(0);
        updateProgress();
    }

    function loadReview(index) {
        if (index >= reviews.length) return;

        currentReviewIndex = index;
        annotations = [];
        annotationOrder = 0;
        deletedAnnotations = [];
        deletionOrder = 0;

        clearSelectionState();

        var reviewEl = document.getElementById('reviewText');
        reviewEl.textContent = reviews[index] || '';

        document.getElementById('reviewTitle').textContent =
            'Review ' + (index + 1) + ' (Click and drag to select text)';

        updateResults();
        updateProgress();
        setupTextSelection();
        scrollPageToTop();
    }

    function clearSelectionState() {
        selectedText = '';
        selectedRange = null;

        if (window.getSelection) {
            window.getSelection().removeAllRanges();
        }

        var buttons = document.querySelectorAll('.attribute-btn');
        buttons.forEach(function(b) {
            b.classList.remove('selected');
        });
    }

    function updateProgress() {
        var progress = (currentReviewIndex / reviews.length) * 100;
        document.getElementById('progressFill').style.width = progress + '%';
        document.getElementById('progressText').textContent =
            'Review ' + (currentReviewIndex + 1) + ' of ' + reviews.length;
    }

    function setupTextSelection() {
        var reviewText = document.getElementById('reviewText');

        var newReviewText = reviewText.cloneNode(true);
        reviewText.parentNode.replaceChild(newReviewText, reviewText);

        newReviewText.addEventListener('mouseup', function() {
            var selection = window.getSelection();
            var selectionText = selection.toString().trim();

            if (selectionText.length > 0 && selection.rangeCount > 0) {
                var range = selection.getRangeAt(0);
                var reviewContainer = document.getElementById('reviewText');

                if (isSelectionWithinReviewText(range, reviewContainer)) {
                    selectedText = selectionText;
                    selectedRange = range.cloneRange();
                } else {
                    clearSelectionState();
                    alert('⚠️ Please select text only from the review content!');
                }
            } else {
                selectedText = '';
                selectedRange = null;
            }
        });
    }

    function isSelectionWithinReviewText(range, reviewContainer) {
        try {
            var startContainer = range.startContainer;
            var endContainer = range.endContainer;

            function isWithinContainer(node, container) {
                while (node && node !== document) {
                    if (node === container) return true;
                    node = node.parentNode;
                }
                return false;
            }

            return isWithinContainer(startContainer, reviewContainer) &&
                   isWithinContainer(endContainer, reviewContainer);
        } catch (e) {
            return false;
        }
    }

    function getTextOffsets(range, container) {
        var preRange = document.createRange();
        preRange.selectNodeContents(container);
        preRange.setEnd(range.startContainer, range.startOffset);

        var start = preRange.toString().length;
        var selected = range.toString();

        return {
            start: start,
            end: start + selected.length
        };
    }

    function getSortedAnnotations() {
        return annotations.slice().sort(function(a, b) {
            if (a.startOffset !== b.startOffset) {
                return a.startOffset - b.startOffset;
            }
            if (a.endOffset !== b.endOffset) {
                return a.endOffset - b.endOffset;
            }
            return a.createdOrder - b.createdOrder;
        });
    }

    function selectAttribute(attr, btn) {
        if (!selectedText || !selectedRange) {
            alert('⚠️ Please select some text from the review first!');
            return;
        }

        var reviewContainer = document.getElementById('reviewText');
        if (!isSelectionWithinReviewText(selectedRange, reviewContainer)) {
            alert('⚠️ Please select text only from the review content!');
            clearSelectionState();
            return;
        }

        var offsets = getTextOffsets(selectedRange, reviewContainer);

        annotationOrder += 1;
        var annId = 'ann_' + currentReviewIndex + '_' + annotationOrder + '_' + Date.now();

        annotations.push({
            attribute: attr,
            text: selectedText,
            id: annId,
            createdOrder: annotationOrder,
            startOffset: offsets.start,
            endOffset: offsets.end
        });

        try {
            var span = document.createElement('span');
            span.className = 'highlight';

            var contents = selectedRange.extractContents();
            span.appendChild(contents);
            span.setAttribute('data-attribute', attr);
            span.setAttribute('annid', annId);
            span.setAttribute('data-start', offsets.start);
            span.setAttribute('data-end', offsets.end);

            selectedRange.insertNode(span);
        } catch (e) {
            // fallback: annotation saved without highlighting
        }

        updateResults();
        clearSelectionState();
    }

    function updateResults() {
        var count = document.getElementById('annotationCount');
        var list = document.getElementById('resultsList');
        var sortedAnnotations = getSortedAnnotations();

        count.textContent = annotations.length;

        if (sortedAnnotations.length === 0) {
            list.innerHTML = '<div class="status-text">No annotations yet. Select text and choose attributes above!</div>';
        } else {
            var html = '';
            sortedAnnotations.forEach(function(ann) {
                html += '<div class="result-item">' +
                            '<div class="result-content">' +
                                '<div class="result-attribute">' + escapeHtml(ann.attribute) + '</div>' +
                                '<div class="result-text">"' + escapeHtml(ann.text) + '"</div>' +
                            '</div>' +
                            '<button class="delete-btn" type="button" onclick="window.deleteAnnotationById(\'' + ann.id + '\')">✕</button>' +
                        '</div>';
            });
            list.innerHTML = html;
        }
    }

    window.deleteAnnotationById = function(id) {
        var index = annotations.findIndex(function(ann) {
            return ann.id === id;
        });

        if (index === -1) return;

        var deletedAnnotation = annotations[index];
        deletionOrder += 1;

        deletedAnnotations.push({
            attribute: deletedAnnotation.attribute,
            text: deletedAnnotation.text,
            createdOrder: deletedAnnotation.createdOrder,
            startOffset: deletedAnnotation.startOffset,
            endOffset: deletedAnnotation.endOffset,
            deletionOrder: deletionOrder
        });

        annotations.splice(index, 1);
        removeHighlightFromText(deletedAnnotation.id);
        updateResults();
    };

    function removeHighlightFromText(id) {
        var reviewDiv = document.getElementById('reviewText');
        var highlights = reviewDiv.querySelectorAll('.highlight');

        highlights.forEach(function(highlight) {
            if (highlight.getAttribute('annid') == id) {
                var parent = highlight.parentNode;
                parent.replaceChild(document.createTextNode(highlight.textContent), highlight);
                parent.normalize();
            }
        });
    }

    function scrollPageToTop() {
        setTimeout(function() {
            window.scrollTo({
                top: 0,
                left: 0,
                behavior: 'smooth'
            });
            document.documentElement.scrollTop = 0;
            document.body.scrollTop = 0;
        }, 0);
    }

    window.moveToNextReview = function() {
        if (annotations.length === 0) {
            alert('⚠️ Please create at least one annotation for this review before continuing.');
            return;
        }

        clearSelectionState();
        saveCurrentReview();

        if (currentReviewIndex < reviews.length - 1) {
            loadReview(currentReviewIndex + 1);
        } else {
            completeAllReviews();
        }
    };

    function saveCurrentReview() {
        var sortedAnnotations = getSortedAnnotations();

        var annotationObjects = sortedAnnotations.map(function(ann, index) {
            return {
                order: index + 1,
                attribute: ann.attribute,
                text: ann.text,
                startOffset: ann.startOffset,
                endOffset: ann.endOffset
            };
        });

        var result = {
            annotator_1: annotationObjects
        };

        allResults[currentReviewIndex] = result;

        var variableName = 'AnnotationResults' + (currentReviewIndex + 1);
        var deletedVariableName = 'deletedReviews' + (currentReviewIndex + 1);

        Qualtrics.SurveyEngine.setEmbeddedData(variableName, JSON.stringify(result));
        Qualtrics.SurveyEngine.setEmbeddedData(deletedVariableName, JSON.stringify(deletedAnnotations));
    }

    function completeAllReviews() {
        document.getElementById('workArea').style.display = 'none';
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('navigationSection').style.display = 'none';
        document.getElementById('completionMessage').style.display = 'block';

        var combinedResults = {
            total_reviews: reviews.length,
            completion_timestamp: new Date().toISOString(),
            all_annotations: allResults
        };

        Qualtrics.SurveyEngine.setEmbeddedData('AllAnnotationResults', JSON.stringify(combinedResults));

        document.getElementById('progressFill').style.width = '100%';
        document.getElementById('progressText').textContent = 'All 6 Reviews Completed!';
    }

    window.finishSurvey = function() {
        alert('✅ All annotation data has been saved successfully!');
        jQuery('#NextButton').click();
    };

    jQuery('#Buttons').hide();
    initialize();
});