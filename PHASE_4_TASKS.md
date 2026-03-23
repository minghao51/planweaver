# Phase 4: Refinement - Task List

## Task Status Legend
- ⏳ TODO
- 🚧 IN PROGRESS
- ✅ COMPLETE
- ❌ BLOCKED

---

## 4.1 Accessibility Audit & Fixes
**Status**: ⏳ TODO
**Priority**: HIGH
**Estimated**: 2-3 hours
**Assignee**: _

### Checklist:
- [ ] Run axe DevTools audit
- [ ] Fix keyboard navigation issues
- [ ] Add ARIA labels to icon buttons
- [ ] Add `aria-live` regions for dynamic content
- [ ] Verify all form inputs have labels
- [ ] Add skip-to-content link
- [ ] Test with screen reader (VoiceOver/NVDA)
- [ ] Fix color contrast issues
- [ ] Test focus management in modals

### Files to Review:
- `src/components/Header.tsx`
- `src/components/NewPlanForm.tsx`
- `src/components/PlanView.tsx`
- `src/components/FlowCanvas.tsx`
- `src/components/panels/QuestionPanel.tsx`
- `src/components/panels/ProposalPanel.tsx`
- `src/components/panels/ExecutionPanel.tsx`
- `src/components/panels/CandidatePlanPanel.tsx`

---

## 4.2 Performance Optimization
**Status**: ⏳ TODO
**Priority**: HIGH
**Estimated**: 2-3 hours
**Assignee**: _

### Checklist:
- [ ] Run Lighthouse audit (target: 90+ all categories)
- [ ] Optimize font loading (add `loading="lazy"`)
- [ ] Add `will-change` hints sparingly
- [ ] Check for layout thrashing
- [ ] Test with CPU throttling (4x)
- [ ] Analyze bundle size
- [ ] Lazy load any remaining heavy components
- [ ] Optimize images (convert to SVG/WebP)
- [ ] Verify all animations use transform/opacity

### Performance Targets:
- First Contentful Paint: < 1.5s
- Time to Interactive: < 3s
- Lighthouse Performance: 90+
- Bundle size: < 500KB gzipped

---

## 4.3 Apply New Components to Panels
**Status**: ⏳ TODO
**Priority**: MEDIUM
**Estimated**: 2-3 hours
**Assignee**: _

### Checklist:

#### QuestionPanel
- [ ] Wrap in CollapsiblePanel
- [ ] Add PanelSkeleton for loading
- [ ] Add status indicators (in-progress for unanswered)
- [ ] Apply FadeInUp animations

#### ProposalPanel
- [ ] Use CardSkeleton for loading states
- [ ] Add FadeInUp to proposal cards
- [ ] Apply hover-lift utility
- [ ] Add selection animations

#### ExecutionPanel
- [ ] Wrap steps in CollapsiblePanel
- [ ] Use ListSkeleton for loading
- [ ] Add animated status indicators
- [ ] Apply step completion animations

#### CandidatePlanPanel
- [ ] Use CardSkeleton during loading
- [ ] Apply ScrollReveal for candidates
- [ ] Add status-based styling
- [ ] Enhance approval interactions

---

## 4.4 Dark Mode Toggle
**Status**: ⏳ TODO
**Priority**: MEDIUM
**Estimated**: 1-2 hours
**Assignee**: _

### Checklist:
- [ ] Create ThemeProvider.tsx
- [ ] Create ThemeToggle.tsx component
- [ ] Add to Header.tsx
- [ ] Update index.css to use data-theme attribute
- [ ] Add localStorage persistence
- [ ] Test theme switching
- [ ] Test system preference detection
- [ ] Add transition animation between themes

### Files to Create:
- `src/components/ThemeProvider.tsx`
- `src/components/ThemeToggle.tsx`

### Files to Modify:
- `src/index.css`
- `src/components/Header.tsx`
- `src/main.tsx`

---

## 4.5 Cross-Browser Testing
**Status**: ⏳ TODO
**Priority**: MEDIUM
**Estimated**: 2-3 hours
**Assignee**: _

### Browser Test Matrix:

| Browser | Version | Tested | Issues | Fixed |
|---------|---------|--------|--------|-------|
| Chrome | 120+ | ⬜ | | |
| Edge | 120+ | ⬜ | | |
| Firefox | 120+ | ⬜ | | |
| Safari | 16+ | ⬜ | | |
| Mobile Safari | iOS 15+ | ⬜ | | |
| Chrome Android | 120+ | ⬜ | | |
| Samsung Internet | 23+ | ⬜ | | |

### Checklist:
- [ ] Test all animations in each browser
- [ ] Verify grid layouts
- [ ] Check scrollbar styling
- [ ] Test backdrop-filter support
- [ ] Verify font loading
- [ ] Test touch interactions on mobile
- [ ] Check safe area insets (notched devices)
- [ ] Add browser-specific CSS fixes if needed

### Known Fixes to Apply:
- [ ] Firefox scrollbar fallback
- [ ] Safari backdrop-filter fallback
- [ ] Grid gap fallback for older browsers
- [ ] -webkit- prefixed properties

---

## 4.6 Documentation
**Status**: ⏳ TODO
**Priority**: LOW
**Estimated**: 1-2 hours
**Assignee**: _

### Checklist:
- [ ] Create DESIGN_SYSTEM.md
- [ ] Create COMPONENT_GUIDE.md
- [ ] Update README.md with design section
- [ ] Add screenshots to documentation
- [ ] Update CLAUDE.md with design notes
- [ ] Document animation preferences
- [ ] Create accessibility guidelines

### Files to Create:
- `frontend/DESIGN_SYSTEM.md`
- `frontend/COMPONENT_GUIDE.md`

### Files to Update:
- `README.md`
- `CLAUDE.md`

---

## Verification Steps

Before marking Phase 4 complete:

### Functional Tests
- [ ] All pages load without errors
- [ ] All forms submit correctly
- [ ] All buttons/links work
- [ ] API integration works
- [ ] SSE updates work
- [ ] ReactFlow renders correctly
- [ ] Theme toggle works (if implemented)

### Visual Tests
- [ ] Light mode looks correct
- [ ] Dark mode looks correct
- [ ] Animations run at 60fps
- [ ] No visual glitches
- [ ] No layout shifts
- [ ] Typography readable at all sizes
- [ ] Colors have sufficient contrast
- [ ] Responsive on all screen sizes

### Performance Tests
- [ ] Lighthouse: Performance 90+
- [ ] Lighthouse: Accessibility 90+
- [ ] Lighthouse: Best Practices 90+
- [ ] Lighthouse: SEO 90+
- [ ] FCP < 1.5s
- [ ] TTI < 3s
- [ ] No memory leaks
- [ ] Bundle size optimized

### Accessibility Tests
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] Focus indicators visible
- [ ] Color contrast meets WCAG AA
- [ ] ARIA labels present
- [ ] Reduced motion respected

---

## Notes

### Browser-Specific CSS to Add:
```css
/* Firefox scrollbar */
@-moz-document url-prefix() {
  * {
    scrollbar-width: thin;
    scrollbar-color: var(--color-surface-light) transparent;
  }
}

/* Safari backdrop-filter */
@supports not (backdrop-filter: blur(16px)) {
  .glass-panel {
    background: var(--color-surface-alt-light);
  }
}

/* Grid gap fallback */
@supports not (gap: 1.5rem) {
  .layout-editorial > * {
    margin: 0.75rem;
  }
}
```

### Testing Commands:
```bash
# Frontend tests
cd frontend && npm run test:run

# E2E tests
cd frontend && npm run e2e

# Type check
cd frontend && npx tsc --noEmit

# Lint
cd frontend && npm run format:check
```

---

## Completion Criteria

Phase 4 is complete when:
1. ✅ All accessibility audits pass
2. ✅ Lighthouse score 90+ in all categories
3. ✅ All panels use new CollapsiblePanel
4. ✅ Theme toggle implemented
5. ✅ Tested in all major browsers
6. ✅ Documentation complete
7. ✅ No console errors
8. ✅ Animations run at 60fps
9. ✅ Bundle optimized
10. ✅ Production ready

---

**Last Updated**: 2026-03-18
**Phase Status**: 0/6 tasks complete
