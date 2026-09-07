# Troubleshooting Guide

Common issues and solutions for video generation.

## Performance Issues

### Video Takes Too Long

**Symptoms:** Generation hangs or takes excessive time
**Causes:**
- v2.0 model processing time (~20-60 seconds for 5s video)
- 2.5-flash rate limiting (1 request per minute)
- Large resolution requests

**Solutions:**
```bash
# Use v2.0 for reliable performance
brandly video <id> --model agnes-video-v2.0 --wait

# Check API status
brandly status
```

### Rate Limiting (429 Errors)

**Symptoms:** "Too Many Requests" error
**Causes:**
- 2.5-flash free tier limits
- Rapid successive requests

**Solutions:**
- Switch to v2.0 model for consistent performance
- Add delays between requests: `sleep 60`
- Queue generation requests

## Quality Issues

### Low Quality Output

**Symptoms:** Blurry, low-detail, artifacts
**Causes:**
- Insufficient prompt detail
- Wrong style for content
- Low resolution request

**Solutions:**
```bash
# Use a higher-quality model (default is already v2.0; 2.5-flash is free but rate-limited)
brandly video <id> --style cinematic --model agnes-video-v2.0 --duration 5

# Add quality keywords to prompt
# "8K, ultra detailed, professional cinematography"
```

### Character Drift Between Shots

**Symptoms:** Character looks different in each shot
**Causes:**
- Insufficient character description
- No reference images used
- Inconsistent prompting

**Solutions:**
- See `references/character-consistency.md`
- Always use --reference-images
- Include full character description in every prompt

### Identity Changes

**Symptoms:** Face, hair, or clothing changes unexpectedly
**Causes:**
- Model interpretation variance
- Missing consistency anchors
- Multiple character descriptions conflicting

**Solutions:**
```
Add explicit consistency anchors:
"MAINTAIN IDENTICAL: face, hair color, outfit, body type"
```

## Technical Issues

### Invalid Project ID

**Symptoms:** "Invalid project ID" error
**Causes:**
- Wrong ID format
- Project doesn't exist
- ID was deleted

**Solutions:**
```bash
# List valid projects
brandly list

# Check project status
brandly status <project_id>
```

### API Connection Errors

**Symptoms:** Connection timeout, network errors
**Causes:**
- Internet connectivity issues
- API server maintenance
- Rate limiting

**Solutions:**
```bash
# Check API key
brandly config --show

# Retry with backoff
brandly video <id> --prompt "..." --wait
```

### Reference Image Issues

**Symptoms:** Reference not applied, incorrect anchoring
**Causes:**
- Invalid URL
- Image format not supported
- Image too small/low quality

**Solutions:**
- Use high-quality reference images (1K+)
- Ensure URLs are publicly accessible
- Test with single reference first

## Prompt Engineering Issues

### Unclear Output

**Symptoms:** Unintended scenes, wrong elements
**Causes:**
- Vague prompt
- Conflicting instructions
- Missing context

**Solutions:**
- Be specific about subjects and actions
- Include environment details
- Use prompt templates from this skill

### Wrong Style Applied

**Symptoms:** Output doesn't match expected style
**Causes:**
- Style keyword missing
- Style contradicts prompt
- Model doesn't support style

**Solutions:**
```bash
# Valid image --style-preset values:
# photorealistic, editorial, cinematic, commercial, documentary
brandly image --prompt "professional studio lighting..." --style-preset commercial

# Valid video --style values:
# cinematic, ugc, montage, multi_shot, continuous, unboxing, lifestyle, ...
brandly video <project_id> --style cinematic --wait
```

## Debugging Checklist

When encountering issues:

1. [ ] Verify API key is valid
2. [ ] Check project exists and is active
3. [ ] Confirm prompt is well-formed
4. [ ] Test with single shot first
5. [ ] Use appropriate style for content
6. [ ] Include reference images when needed
7. [ ] Check network connectivity
8. [ ] Review error messages carefully

## Getting Help

If issues persist:

1. Check the API status page
2. Review error logs: `brandly logs`
3. Test with minimal prompt
4. Try different model (v2.0 vs 2.5-flash)
5. Consult documentation or support
